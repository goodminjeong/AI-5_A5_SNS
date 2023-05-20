from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import JsonResponse
from django.views.generic import ListView, TemplateView
from .forms import PostForm, CommentForm
from .models import Post, Comment
from user.models import User as user_model
from post import models
from post.serializers import PostSerializer
from . import serializers


# Create your views here.


@login_required(login_url='')
def write_post(request):
    """게시글을 작성하는 함수"""
    if request.method == 'GET':
        form = PostForm()
        return render(request, 'post/write-post.html', {'form': form})

    elif request.method == 'POST':
        user = get_object_or_404(user_model, pk=request.user.id)
        post_form = PostForm(request.POST, request.FILES)
        if post_form.is_valid():
            write_post = post_form.save(commit=False)
            write_post.author = user
            write_post.save()
            post_form.save_m2m()
            return redirect('post:feed')
        else:
            return redirect('user:signup')


@login_required(login_url='')
def edit_post(request, post_id):
    """게시글을 수정하는 함수"""
    edit_post = Post.objects.get(id=post_id)
    current_edit_post = edit_post.id

    if request.method == 'GET':
        edit_form = PostForm(instance=edit_post)
        context = {
            'form': edit_form,
            'edit': '수정하기',
        }
        return render(request, 'post/edit-post.html', context)

    elif request.method == 'POST':
        user = get_object_or_404(user_model, pk=request.user.id)
        edit_form = PostForm(request.POST, request.FILES, instance=edit_post)
        if edit_form.is_valid():
            edit_post = edit_form.save(commit=False)
            edit_post.author = user
            edit_post.id = current_edit_post
            edit_post.save()
            return redirect(reverse('post:feed') + "#post-" + str(edit_post.id))


@login_required(login_url='')
def delete_post(request, post_id):
    """게시글을 삭제하는 함수"""
    delete_post = Post.objects.get(id=post_id)
    delete_post.delete()
    return redirect('post:feed')


@login_required(login_url='')
def user_feed(request):
    """피드(홈) 페이지"""
    if request.method == 'GET':
        comment_form = CommentForm()
        post_list = Post.objects.all().order_by('-id')

        serializer = serializers.PostSerializer(post_list, many=True)

        return render(request, 'post/posts.html', {'posts': serializer.data, 'comment_form': comment_form})


@login_required(login_url='')
def search(request):
    """검색 함수"""
    if request.user.is_authenticated:
        if request.method == "GET":
            search_keyword = request.GET.get("q", "")
            comment_form = CommentForm()

            # 검색어가 포함된 caption과 username을 모두 찾음
            posts = Post.objects.filter(Q(caption__contains=search_keyword) | Q(
                author__username__contains=search_keyword))

            serializer = serializers.PostSerializer(posts, many=True)
            return render(request, 'post/posts.html', {'posts': serializer.data, 'comment_form': comment_form})


@login_required(login_url='')
def comment_create(request, post_id):
    """댓글 작성 함수"""
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.posts = post
        comment.save()

        return redirect(reverse('post:feed') + "#comment-" + str(comment.id))

    else:
        post_list = Post.objects.all().order_by('-id')
        comment_form = CommentForm()

        return render(request, 'post/posts.html', {'posts': post_list, 'comment_form': comment_form})


@login_required(login_url='')
def comment_delete(request, comment_id):
    """댓글 삭제 함수"""
    comment = get_object_or_404(Comment, pk=comment_id)
    if request.user == comment.author:
        comment.delete()

    return redirect(reverse('post:feed'))


@login_required(login_url='')
def post_like(request, post_id):
    """좋아요 함수"""
    response_body = {"result": ""}

    if request.method == "POST":
        post = get_object_or_404(Post, pk=post_id)
        like_user = post.post_likes.filter(pk=request.user.id).exists()
        if like_user:
            post.post_likes.remove(request.user)
            result = 'dislike'
        else:
            post.post_likes.add(request.user)
            result = 'like'

        response_body = {
            'result': result,
            'like_count': post.like_count,
        }
        post.save()
        # https://developer.mozilla.org/ko/docs/Web/HTTP/Status
        return JsonResponse(status=200, data=response_body)


# 태그 추가해줄 함수들
class TagCloudTV(TemplateView):
    template_name = 'taggit/tag_cloud.html'


class TaggedObjectLV(ListView):
    template_name = 'post/posts.html'
    model = Post

    def get_queryset(self):
        return Post.objects.filter(tags__name=self.kwargs.get('tag'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tagname"] = self.kwargs["tag"]
        context["posts"] = serializers.PostSerializer(
            context["object_list"], many=True).data

        return context
