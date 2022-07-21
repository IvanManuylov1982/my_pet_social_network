from django.core.paginator import Paginator

PAGE_ON_LIST: int = 10


def get_page_context(post_list, request):
    paginator = Paginator(post_list, PAGE_ON_LIST)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return {
        'page_obj': page_obj,
    }
