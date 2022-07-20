import tempfile
import shutil

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

from posts.models import Post, Group, Comment, Follow

User = get_user_model()

FIRST_PAGE_LEN_POSTS: int = 10
SECOND_PAGE_LEN_POSTS: int = 3
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create(
            username='post_author',
        )
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test-slug',
            description='Тестовое описание группы',
        )
        cls.post = Post.objects.create(
            text='Рандомный текст',
            author=PostViewTests.user,
            group=PostViewTests.group,
            image=uploaded,
        )
        cls.comment_post = Comment.objects.create(
            author=cls.user,
            text='Что тут комментировать',
            post=cls.post
        )
        cls.group_fake = Group.objects.create(
            title='Фейк группа',
            slug='fake-slug',
            description='Описание фейк группы',
        )
        cls.templates_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': cls.group.slug,
                            }): 'posts/group_list.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:profile',
                    kwargs={'username': cls.user.username,
                            }): 'posts/profile.html',
        }

    @classmethod
    def tearDownClass(cls):
        """Удаляем тестовые медиа."""
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        """Создаем клиент зарегистрированного пользователя."""
        self.authorized_client = Client()
        self.authorized_client.force_login(PostViewTests.user)
        cache.clear()

    def test_views_use_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for reverse_name, template in PostViewTests.templates_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_pages_show_correct_context(self):
        context = {reverse('posts:index'): self.post,
                   reverse('posts:group_list',
                   kwargs={'slug': self.group.slug,
                           }): self.post,
                   reverse('posts:profile',
                   kwargs={'username': self.user.username,
                           }): self.post,
                   }
        for reverse_page, object in context.items():
            with self.subTest(reverse_page=reverse_page):
                response = self.authorized_client.get(reverse_page)
                page_object = response.context['page_obj'][0]
                self.assertEqual(page_object.text, object.text)
                self.assertEqual(page_object.pub_date, object.pub_date)
                self.assertEqual(page_object.author, object.author)
                self.assertEqual(page_object.group, object.group)
                self.assertEqual(page_object.image, object.image)

    def test_groups_page_show_correct_context(self):
        context = {reverse('posts:group_list',
                   kwargs={'slug': self.group.slug}): self.group,
                   reverse('posts:group_list',
                   kwargs={'slug': self.group_fake.slug}): self.group_fake,
                   }
        response = self.authorized_client.get(
            reverse('posts:group_list',
                    kwargs={'slug': self.group_fake.slug}))
        self.assertFalse(response.context['page_obj'])
        for reverse_page, object in context.items():
            with self.subTest(reverse_page=reverse_page):
                response = self.authorized_client.get(reverse_page)
                group_object = response.context['group']
                self.assertEqual(group_object.title, object.title)
                self.assertEqual(group_object.slug, object.slug)
                self.assertEqual(group_object.description,
                                 object.description)

    def test_forms_show_correct_instance(self):
        context = {
            reverse('posts:post_create'),
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.id,
                            }),
        }
        for reverse_page in context:
            with self.subTest(reverse_page=reverse_page):
                response = self.authorized_client.get(reverse_page)
                self.assertIsInstance(response.context['form'].fields['text'],
                                      forms.fields.CharField)
                self.assertIsInstance(response.context['form'].fields['group'],
                                      forms.fields.ChoiceField)

    def test_follow(self):
        """Тестирование подписки на автора."""
        count_follow = Follow.objects.count()
        new_author = User.objects.create(username='Lermontov')
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': new_author.username}
            )
        )
        follow = Follow.objects.last()
        self.assertEqual(Follow.objects.count(), count_follow + 1)
        self.assertEqual(follow.author, new_author)
        self.assertEqual(follow.user, PostViewTests.user)

    def test_unfollow(self):
        """Тестирование отписки от автора."""
        count_follow = Follow.objects.count()
        new_author = User.objects.create(username='Lermontov')
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': new_author.username}
            )
        )
        self.assertEqual(Follow.objects.count(), count_follow + 1)
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': new_author.username}
            )
        )
        self.assertEqual(Follow.objects.count(), count_follow)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(
            username='posts_author',
        )
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test-slug',
            description='Тестовое описание группы',
        )
        paginator_objects = []
        for i in range(13):
            new_post = Post(
                text='Пост №' + str(i),
                author=PaginatorViewsTest.user,
                group=PaginatorViewsTest.group
            )
            paginator_objects.append(new_post)
        cls.post = Post.objects.bulk_create(paginator_objects)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PaginatorViewsTest.user)
        cache.clear()

    def test_paginator_on_pages(self):
        context = {
            reverse('posts:index'): FIRST_PAGE_LEN_POSTS,
            reverse('posts:index') + '?page=2': SECOND_PAGE_LEN_POSTS,
            reverse('posts:group_list', kwargs={'slug': self.group.slug, }):
            FIRST_PAGE_LEN_POSTS,
            reverse('posts:group_list', kwargs={'slug': self.group.slug, })
            + '?page=2': SECOND_PAGE_LEN_POSTS,
            reverse('posts:profile', kwargs={'username': self.user.username}):
            FIRST_PAGE_LEN_POSTS,
            reverse('posts:profile', kwargs={'username': self.user.username})
            + '?page=2': SECOND_PAGE_LEN_POSTS,
        }
        for reverse_page, len_posts in context.items():
            with self.subTest(reverse=reverse):
                self.assertEqual(len(self.authorized_client.get(
                    reverse_page).context['page_obj']), len_posts)


class CacheIndexPageTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(
            username='posts_author',
        )

    def setUp(self):
        # Авторизовываем пользователя
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_cache(self):
        content = self.authorized_client.get(reverse('posts:index')).content
        Post.objects.create(
            text='Пост №1',
            author=self.user,
        )
        content_1 = self.authorized_client.get(reverse('posts:index')).content
        self.assertEqual(content, content_1)
        cache.clear()
        content_2 = self.authorized_client.get(reverse('posts:index')).content
        self.assertNotEqual(content_1, content_2)
