from django.db import models
from django.utils import timezone

from users.models import User


class ArticleCategory(models.Model):
    '''
    文章分类
    '''
    # 分类标题
    title = models.CharField(max_length=100, blank=True)
    # 分类的创建时间
    created = models.DateTimeField(default=timezone.now)

    # admin站点显示，调试查看对象方便
    def __str__(self):
        return self.title

    class Meta:
        db_table = 'tb_category'  # 修改表名
        verbose_name = '类别管理'  # admin站点显示; 别名
        verbose_name_plural = verbose_name  # 复数形式=单数形式，可以去除后面的s


class Article(models.Model):
    # 作者
    # 参数no_delete就是当user表中的数据删除之后，文章信息也同步删除
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    # 标题图
    avatar = models.ImageField(upload_to='article/%Y%m%d/', blank=True)

    # 标题
    title = models.CharField(max_length=20, blank=True)
    # 分类
    category = models.ForeignKey(ArticleCategory, null=True, blank=True, on_delete=models.CASCADE, related_name='article')
    # 标签
    tags = models.CharField(max_length=20, blank=True)
    # 摘要信息
    sumary = models.CharField(max_length=300, null=False, blank=False)
    # 文章正文
    content = models.TextField()
    # 浏览量
    total_views = models.PositiveIntegerField(default=0)
    # 评论量
    comments_count = models.PositiveIntegerField(default=0)
    # 文章创建时间
    created = models.DateTimeField(default=timezone.now)
    # 文章修改时间
    updated = models.DateTimeField(auto_now=True)

    # 修改表名以及admin展示的配置信息等
    class Meta:
        db_table = 'tb_article'
        # 对模型返回数据进行默认排序
        # 根据其创建时间进行排序,'-created' 表明数据应该以倒序排列
        ordering = ('-created',)
        verbose_name = '文章管理'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title


class Comment(models.Model):
    # 评论内容
    content = models.TextField()
    # 评论文章
    article = models.ForeignKey(Article, on_delete=models.SET_NULL, null=True)
    # 评论用户
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    # 评论时间
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.article.title

    class Meta:
        db_table = 'tb_comment'
        verbose_name = '评论管理'
        verbose_name_plural = verbose_name