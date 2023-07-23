from django.http import Http404
from django.shortcuts import (render, get_object_or_404, get_list_or_404,
                              redirect)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (ListView, CreateView, UpdateView, DeleteView,
                                  DetailView)
from blog.models import Post, Category, User, Comment
from django.utils import timezone
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from .forms import PostForm, EditProfileForm, CommentForm
from django.db.models import Count

POSTS_PER_PAGE = 10


class PostListView(ListView):
    model = Post
    template_name = 'blog/index.html'
    paginate_by = POSTS_PER_PAGE

    def get_queryset(self):
        return Post.objects.filter(
            is_published=True,
            category__is_published=True,
            pub_date__lt=timezone.now()).order_by('-pub_date',
                                                  'title').annotate(
            comment_count=Count('comment'))


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

        base_condition = {
            'is_published': True,
            'category__is_published': True,
            'pub_date__lt': timezone.now(),
        }

        posts = Post.objects.filter(**base_condition).order_by('-pub_date',
                                                               'title')
        comments = Comment.objects.filter(post=post).order_by('created_at')
        comment_form = CommentForm()
        context['form'] = comment_form
        context['comments'] = comments
        context['posts'] = posts

        return context


def category_posts(request, category_slug):
    template = 'blog/category.html'
    category = get_object_or_404(Category, slug=category_slug)
    post_list = get_list_or_404(category.posts.filter(
        category__slug=category_slug,
        is_published=True,
        category__is_published=True,
        pub_date__lt=timezone.now()).order_by('-pub_date', 'title'))
    paginator = Paginator(post_list, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
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
            category__slug=category_slug,
            is_published=True,
            category__is_published=True,
            pub_date__lt=timezone.now()
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

    paginator = Paginator(posts, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'profile': profile,
        'page_obj': page_obj
    }
    return render(request, 'blog/profile.html', context)


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    template_name = 'blog/comment.html'
    fields = ('text',)

    def form_valid(self, form):
        post = get_object_or_404(Post, pk=self.kwargs['pk'])
        form.instance.author = self.request.user
        form.instance.post = post
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('blog:post_detail',
                            kwargs={'pk': self.kwargs['pk']})


class CommentDeleteView(LoginRequiredMixin, DeleteView):
    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comm_pk'

    def dispatch(self, request, *args, **kwargs):
        comment = self.get_object()

        if comment.author != request.user and not request.user.is_superuser:
            raise Http404()

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('blog:post_detail',
                            kwargs={'pk': self.object.post.pk})


class CommentUpdateView(LoginRequiredMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comm_pk'

    def dispatch(self, request, *args, **kwargs):
        comment = self.get_object()

        if comment.author != request.user:
            raise Http404()

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('blog:post_detail',
                            kwargs={'pk': self.kwargs['pk']})


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = EditProfileForm
    template_name = 'blog/user.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return reverse_lazy('blog:profile',
                            kwargs={'username': self.request.user})


class ProfileDetail(DetailView):
    model = User
    template_name = 'blog/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = get_object_or_404(User, username=self.kwargs['username'])
        context['profile'] = profile

        return context

    def get_success_url(self):
        return reverse_lazy('blog:profile',
                            kwargs={'username': self.request.user})


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('blog:profile',
                            kwargs={'username': self.request.user})


class PostUpdateView(LoginRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def dispatch(self, request, *args, **kwargs):
        instance = get_object_or_404(Post, id=self.kwargs['pk'])
        if instance.author != request.user:
            return redirect('blog:post_detail', pk=self.kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('blog:post_detail',
                            kwargs={'pk': self.kwargs['pk']})


class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance = self.get_object()
        context['form'] = PostForm(instance=instance)
        return context

    def dispatch(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author != self.request.user:
            return redirect('blog:post_detail', pk=self.kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('blog:profile',
                            kwargs={'username': self.request.user})
