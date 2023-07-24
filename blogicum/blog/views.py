from django.http import Http404
from django.shortcuts import (render, get_object_or_404, get_list_or_404,
                              redirect)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (ListView, CreateView, UpdateView, DeleteView,
                                  DetailView)
from django.utils import timezone
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.db.models import Count

from .forms import PostForm, EditProfileForm, CommentForm
from .models import Post, Category, User, Comment
from blogicum.settings import POSTS_PER_PAGE

BASE_FILTER_FOR_POSTS = {
    'is_published': True,
    'category__is_published': True,
    'pub_date__lt': timezone.now(),
}


class PostListView(ListView):
    model = Post
    template_name = 'blog/index.html'
    paginate_by = POSTS_PER_PAGE

    def get_queryset(self):
        return Post.objects.filter(**BASE_FILTER_FOR_POSTS).order_by(
            '-pub_date', 'title').annotate(comment_count=Count('comment'))


def my_paginator(request, posts):
    paginator = Paginator(posts, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


def category_posts(request, category_slug):
    template = 'blog/category.html'
    category = get_object_or_404(Category, slug=category_slug)
    post_list = get_list_or_404(category.posts.filter(
        category__slug=category_slug, **BASE_FILTER_FOR_POSTS).order_by(
        '-pub_date', 'title'))
    page_obj = my_paginator(request, post_list)
    context = {'category': category, 'page_obj': page_obj}
    return render(request, template, context)


class CategoryPostsListView(ListView):
    model = Post
    template_name = 'blog/category.html'
    context_object_name = 'page_obj'
    paginate_by = POSTS_PER_PAGE

    def get_queryset(self):
        category_slug = self.kwargs.get('category_slug')
        category = get_object_or_404(Category, slug=category_slug)

        queryset = category.posts.filter(
            category__slug=category_slug, **BASE_FILTER_FOR_POSTS
        ).order_by('-pub_date', 'title').annotate(
            comment_count=Count('comment'))

        return queryset

    def dispatch(self, request, *args, **kwargs):
        category_slug = self.kwargs.get('category_slug')
        category = get_object_or_404(Category, slug=category_slug)

        if not category.is_published:
            raise Http404()

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category_slug = self.kwargs.get('category_slug')
        category = get_object_or_404(Category, slug=category_slug)
        context['category'] = category
        return context


def profile_view(request, username):
    profile = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author=profile.pk).order_by(
        '-pub_date').annotate(comment_count=Count('comment'))
    page_obj = my_paginator(request, posts)

    context = {
        'profile': profile,
        'page_obj': page_obj
    }
    return render(request, 'blog/profile.html', context)


class CommentMixin:
    model = Comment
    template_name = 'blog/comment.html'

    def get_success_url(self):
        return reverse_lazy('blog:post_detail',
                            kwargs={'pk': self.kwargs['pk']})


class CommentCreateView(LoginRequiredMixin, CommentMixin, CreateView):
    fields = ('text',)

    def form_valid(self, form):
        post = get_object_or_404(Post, pk=self.kwargs['pk'])
        form.instance.author = self.request.user
        form.instance.post = post
        return super().form_valid(form)


class CommentDeleteView(LoginRequiredMixin, CommentMixin, DeleteView):
    pk_url_kwarg = 'comm_pk'

    def dispatch(self, request, *args, **kwargs):
        comment = self.get_object()

        if comment.author != request.user and not request.user.is_superuser:
            raise Http404()

        return super().dispatch(request, *args, **kwargs)


class CommentUpdateView(LoginRequiredMixin, CommentMixin, UpdateView):
    form_class = CommentForm
    pk_url_kwarg = 'comm_pk'

    def dispatch(self, request, *args, **kwargs):
        comment = self.get_object()

        if comment.author != request.user:
            raise Http404()

        return super().dispatch(request, *args, **kwargs)


class ProfileMixin:
    model = User

    def get_success_url(self):
        return reverse_lazy('blog:profile',
                            kwargs={'username': self.request.user})


class ProfileUpdateView(LoginRequiredMixin, ProfileMixin, UpdateView):
    form_class = EditProfileForm
    template_name = 'blog/user.html'

    def get_object(self, queryset=None):
        return self.request.user


class ProfileDetail(ProfileMixin, DetailView):
    template_name = 'blog/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = get_object_or_404(User, username=self.kwargs['username'])
        context['profile'] = profile

        return context


class PostMixin:
    model = Post
    # Стоит ли model вынести в еще один Mixin, чтобы можно
    # было наследовать к PostDetailView?
    template_name = 'blog/create.html'

    def get_success_url(self):
        return reverse_lazy('blog:profile',
                            kwargs={'username': self.request.user})


class PostExistsMixin:
    """Edit and Delete posts"""

    def dispatch(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author != self.request.user:
            return redirect('blog:post_detail', pk=self.kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)


class PostCreateView(LoginRequiredMixin, PostMixin, CreateView):
    form_class = PostForm

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class PostUpdateView(LoginRequiredMixin, PostMixin, PostExistsMixin,
                     UpdateView):
    form_class = PostForm


class PostDeleteView(LoginRequiredMixin, PostMixin, PostExistsMixin,
                     DeleteView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance = self.get_object()
        context['form'] = PostForm(instance=instance)
        return context


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        post = context['post']

        if not post.is_published and (
                not user.is_authenticated or post.author != user):
            raise Http404()

        if not post.category.is_published and (
                not user.is_authenticated or post.author != user):
            raise Http404()

        if post.pub_date > timezone.now() and (
                not user.is_authenticated or post.author != user):
            raise Http404()

        posts = Post.objects.filter(**BASE_FILTER_FOR_POSTS).order_by(
            '-pub_date', 'title')
        comments = Comment.objects.filter(post=post).order_by('created_at')
        comment_form = CommentForm()
        context['form'] = comment_form
        context['comments'] = comments
        context['posts'] = posts

        return context
