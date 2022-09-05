from django.db import models
from django.contrib.auth.models import User, AbstractUser


class User(AbstractUser):
    # 手机号
    mobile = models.CharField(max_length=11, unique=True, blank=False)
    # 头像信息,upload_to指定了图片上传的位置，即/media/avatar/%Y%m%d/
    # #%Y%m%d是日期格式化的写法，会最终格式化为系统时间
    # 注意 ImageField字段不会存储图片本身，而仅仅保存图片的地址。
    # 记得用pip指令安装Pillow。
    avatar = models.ImageField(upload_to='avatar/%Y%m%d', blank=True)
    # 简介信息
    user_desc = models.CharField(max_length=500, blank=True)

    # 修改认证的字段为手机号
    USERNAME_FIELD = 'mobile'

    # 创建超级管理员必须输入的字典（不包括 手机号和密码）
    REQUIRED_FIELDS = ['username', 'email']

    class Meta:
        db_table = 'tb_users'  # 修改表名
        verbose_name = '用户信息'  # Admin后台显示
        verbose_name_plural = verbose_name  # Admin后台显示

    def __str__(self):
        return self.mobile