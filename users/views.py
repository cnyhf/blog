from random import randint

from django.db import DatabaseError
from django.http import HttpResponseBadRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import View
from django_redis import get_redis_connection
from libs.captcha.captcha import captcha
from libs.yuntongxun.sms import CCP
from users.models import User
from utils.response_code import RETCODE
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from home.models import ArticleCategory, Article
import logging
import re
logger = logging.getLogger('django')


class RegisterView(View):
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        # 1,接收数据
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        # 短信验证码
        smscode = request.POST.get('sms_code')
        # 2，验证数据
        #     2.1 参数是否齐全
        if not all([mobile, password, password2, smscode]):
            return HttpResponseBadRequest('缺少必要参数')
        #     2.2 手机号格式是否正确
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('手机号不符合规则')
        #     2.3 密码是否是8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('请输入8-20位的密码')
        #     2.4 密码和确认密码要一致
        if password != password2:
            return HttpResponseBadRequest('两次输入密码不一致')
        #     2.5 短信验证码是否和redis中的一致
        redis_conn = get_redis_connection('default')
        redis_sms_code = redis_conn.get('sms:%s' % mobile)
        if redis_sms_code is None:
            return HttpResponseBadRequest('短信验证码已过期')
        if smscode != redis_sms_code.decode():
            return HttpResponseBadRequest('短信验证码不一致')
        # 3，保存注册信息
        # create_user 可以使用系统的方法对密码进行加密
        try:
            user = User.objects.create_user(username=mobile,
                                        mobile=mobile,
                                        password=password)
        except DatabaseError as e:
            logger.error(e)
            return HttpResponseBadRequest('注册失败')
        login(request, user)
        # 4，返回响应跳转到指定页面
        # redirect进行重定向,
        # reverse是可以通过namespace：name来获取视图所对应的路由
        return redirect(reverse('home:index'))
        # 设置cookie,以方便首页中用户信息的展示
        # 登录状态，会话结束后自动过期
        response.set_cookie('is_login', True)
        # 设置用户名有效期一个月
        response.set_cookie('username', user.username, max_age=30 * 24 * 3600)

        return response


class ImageCodeView(View):
    def get(self, request):

        # 1.接收前端传递过来的uuid
        uuid = request.GET.get('uuid')
        # 2.判断uuid是否获取到
        if uuid is None:
            return HttpResponseBadRequest('请求参数错误')

        # 3.通过调用captcha来生成图片验证码（图片内容和图片二进制）
        text, image = captcha.generate_captcha()

        # 4.将图片内容保存到redis中，uuid作为一个key，图片内容作为一个value
        # 同时我们还需要设置一个时效
        redis_conn = get_redis_connection('default')
        # key:uuid, second, value
        redis_conn.setex('img:%s' % uuid, 300, text)

        # 5.返回图片二进制
        return HttpResponse(image, content_type='image/jpeg')


class SmsCodeView(View):
    def get(self, request):

        # 1，接收参数（查询字符串）
        mobile = request.GET.get('mobile')
        image_code = request.GET.get('image_code')
        uuid = request.GET.get('uuid')
        # 2，参数的验证
        #     2.1验证参数是否齐全
        if not all([mobile, image_code, uuid]):
            return JsonResponse({'code': RETCODE.NECESSARYPARAMERR, 'errmsg': '缺少必要的参数'})
        #     2.2图片验证码验证
        #         连接redis
        redis_conn = get_redis_connection('default')
        #         获取redis中的图片验证码
        redis_image_code = redis_conn.get('img:%s' % uuid)
        #         判断图片验证码是否存在
        if redis_image_code is None:
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图片验证码已过期'})
        #         如果图片验证码未过期，我们获取到之后就可以删除图片验证码
        # 一码一用，验证码不能被反复使用,我验证过了，我再提交，不能被通过
        try:
            redis_conn.delete('img: %s' % uuid)
        except Exception as e:
            logger.error(e)
        #         比对图片验证码,注意大小写问题，redis的数据是bytes类型
        if redis_image_code.decode().lower() != image_code.lower():
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图片验证码错误'})
        # 3，生成短信验证码
        sms_code = '%06d' % randint(0, 999999)
        # 为了后期比对方便，我们可以将短信验证码记录到日志中
        logger.info(sms_code)
        # 4，保存短信验证码到redis中
        redis_conn.setex('sms:%s' % mobile, 300, sms_code)
        # redis_sms_code = redis_conn.get('sms:%s' % mobile)
        # print(redis_sms_code.decode())
        # 5，发送短信
        CCP().send_template_sms(mobile, [sms_code, 5], 1)
        # 6，返回响应
        return JsonResponse({'code': RETCODE.OK, 'errmsg': '短信发送成功'})


class LoginView(View):
    def get(self, request):

        return render(request, 'login.html')

    def post(self,request):
        # 1，接收参数
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        # 可选的参数：记录状态
        remember = request.POST.get('remember')
        # 2，参数验证
        #     2.1验证手机号是否符合规则
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('手机号不符合规则')
        #     2.2验证密码是否符合规则
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('密码不符合规则')
        # 3，用户认证登陆
        # 采用系统自带的认证方法进行认证
        # 如果我们的用户名和密码正确，会返回user,如果不正确会返回None
        # 默认的方法是 对于username字段进行用户名的判断，
        # 当前判断信息是手机号，所以我们需要修改一下认证字段
        user = authenticate(mobile=mobile, password=password)
        if user is None:
            return HttpResponseBadRequest('用户名或密码错误')
        # 4，状态保持
        login(request, user)
        # 5，根据用户选择的是否记录登陆状态来进行判断
        # 6，为了首页现实我们需要设置一些cookies信息

        # 根据next参数来进行页面的跳转
        next_page = request.GET.get('next')
        if next_page:
            response = redirect(next_page)
        else:
            response = redirect(reverse('home:index'))
        if remember != 'on':  # 没有记住用户信息
            # 浏览器关闭之后
            request.session.set_expiry(0)
            response.set_cookie('is_login', True)
            response.set_cookie('username', user.username, max_age=(14*24*3600))
        else:  # 记住用户信息
            # 默认是记住两周
            request.session.set_expiry(None)
            response.set_cookie('is_login', True, max_age=14*24*3600)
            response.set_cookie('username', user.username, max_age=(14*24*3600))
        # 7，返回响应
        return response


class LogoutView(View):
    def get(self,request):
        # 1，session数据清除
        logout(request)
        # 2，删除部分cookie数据
        # 退出登录，重定向到登录页
        response = redirect(reverse('home:index'))
        # 退出登录时清除cookie中的登录状态
        response.delete_cookie('is_login')
        # 3，跳转到首页
        return response


class ForgetPasswordView(View):
    def get(self,request):
        return render(request, 'forget_password.html')

    def post(self, request):
        # 1,接收数据，获取提交的账号，新密码，确认密码,短信验证码
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        smscode = request.POST.get('sms_code')
        # 2,验证数据
        #   2.1 验证参数是否齐全
        if not all([mobile, password, password2, smscode]):
            return HttpResponseBadRequest('参数不全')
        #   2.2 验证手机号是否符合规则
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('手机号不符合规则')
        #   2.3 验证新密码格式是否正确
        if not re.match(r'^[0-9A-Za-z]{8,12}$', password):
            return HttpResponseBadRequest('密码格式不正确')
        #   2.4 验证两次密码输入是否一致
        if password != password2:
            return HttpResponseBadRequest('两次密码输入不一致，请重新输入')
        #   2.5 验证短信验证码是否正确
        redis_conn = get_redis_connection('default')
        redis_sms_code = redis_conn.get('sms:%s' % mobile)
        if redis_sms_code is None:
            return HttpResponseBadRequest('短信验证码已过期')
        if redis_sms_code.decode() != smscode:
            return HttpResponseBadRequest('短信验证码错误')
        # 3.根据手机号在数据库中查询用户信息
        try:
            user = User.objects.get(mobile = mobile)
        except User.DoesNotExist:
            # 5.如果手机号没有查询出用户信息，则进行新用户创建
            try:
                User.objects.create_user(username=mobile,
                                        mobile=mobile,
                                        password=password)
            except Exception:
                return HttpResponseBadRequest('修改失败，请稍候再试')

        else:
            # 4.如果手机号查询出用户信息则进行密码修改
            user.set_password(password)
            # 注意保存用户信息
            user.save()
        # 6.页面跳转到登陆页面
        response = redirect(reverse('users:login'))
        # 7.返回响应
        return response

# 如果用户未登录的话，则会进行默认的跳转
# 默认的跳转连接是：accounts/login/?next=xxx


class UserCenterView(LoginRequiredMixin, View):
    def get(self, request):
        # 获取登陆用户信息
        user = request.user
        # 组织获取用户信息
        context = {
            'username': user.username,
            'mobile': user.mobile,
            # 用户头像
            'avatar': user.avatar.url if user.avatar else None,
            # 用户简介
            'user_desc': user.user_desc
        }
        return render(request, 'center.html', context=context)

    def post(self, request):
        user = request.user
        # 1.接收参数
        username = request.POST.get('username', user.username)
        avatar = request.FILES.get('avatar')
        user_desc = request.POST.get('desc', user.user_desc)
        # 2.将参数保存到数据库中，头像保存在指定目录中
        try:
            user.username = username
            user.user_desc = user_desc
            if avatar:
                user.avatar = avatar
                user.save()
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('修改失败，请稍候再试')

        # 3.刷新当前页面（重定向操作）
        response = redirect(reverse('users:center'))
        # 4.更新cookie中的username信息
        response.set_cookie('username', user.username, max_age=14*3600*24)

        # 5.返回响应
        return response


class WriteBlogView(LoginRequiredMixin, View):
    def get(self, request):
        # 查询所有分类模型
        categories = ArticleCategory.objects.all()
        context = {
            'categories': categories
        }
        return render(request, 'write_blog.html', context=context)

    def post(self,request):
        # 1.接收数据
        avatar = request.FILES.get('avatar')
        title = request.POST.get('title')
        category_id = request.POST.get('category')
        tags = request.POST.get('tags')
        sumary = request.POST.get('sumary')
        content = request.POST.get('content')
        user = request.user
        # 2.验证数据
        #     2.1 验证参数是否齐全
        if not all([avatar, title, category_id, sumary, content]):
            return HttpResponseBadRequest('参数不全')
        #     2.2 判断分类id
        try:
            category = ArticleCategory.objects.get(id=category_id)
        except ArticleCategory.DoesNotExist:
            return HttpResponseBadRequest('没有此分类')
        # 3.数据入库
        try:
            article = Article.objects.create(
                author=user,
                avatar=avatar,
                title=title,
                category=category,
                tags=tags,
                sumary=sumary,
                content=content
             )
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('发布失败，请稍后再试')
        # 4.跳转到指定页面
        response = redirect(reverse('home:index'))
        return response









































