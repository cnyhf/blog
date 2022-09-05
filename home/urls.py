# coding=utf-8
# time :2022/8/21
from django.urls import path

from home.views import IndexView, DetailView

urlpatterns = [
    # 首页的路由
    path('', IndexView.as_view(), name='index'),
    # 详情视图的路由
    path('detail/', DetailView.as_view(), name='detail'),
]