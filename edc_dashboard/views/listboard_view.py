import six

from django.apps import apps as django_apps
from django.views.generic.list import ListView

from ..view_mixins import UrlRequestContextMixin, TemplateRequestContextMixin
from ..view_mixins import QueryStringViewMixin, SearchListboardMixin
from ..view_mixins import SiteQuerysetViewMixin, ListboardPermmissionMixin


class ListboardViewError(Exception):
    pass


class BaseListboardView(TemplateRequestContextMixin, ListView):

    cleaned_search_term = None
    context_object_name = "results"
    empty_queryset_message = "Nothing to display."
    listboard_template = None  # an existing key in request.context_data
    # if self.listboard_url declared through another mixin.
    listboard_url = None  # an existing key in request.context_data

    # default, info, success, danger, warning, etc. See Bootstrap.
    listboard_panel_style = "default"
    listboard_fa_icon = "fas fa-user-circle"
    listboard_model = None  # label_lower model name or model class
    listboard_model_manager_name = "_default_manager"
    listboard_panel_title = None

    model_wrapper_cls = None
    ordering = "-created"

    orphans = 3
    paginate_by = 10
    paginator_url = None  # defaults to listboard_url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = context.get(self.context_object_name)
        context_object_name = self.get_context_object_name(queryset)
        wrapped_queryset = self.get_wrapped_queryset(queryset)
        if self.listboard_fa_icon and self.listboard_fa_icon.startswith("fa-"):
            self.listboard_fa_icon = f"fas {self.listboard_fa_icon}"
        context.update(
            empty_queryset_message=self.empty_queryset_message,
            listboard_fa_icon=self.listboard_fa_icon,
            listboard_panel_style=self.listboard_panel_style,
            listboard_panel_title=self.listboard_panel_title,
            object_list=wrapped_queryset,
        )
        if context_object_name is not None:
            context[context_object_name] = wrapped_queryset
        context = self.add_url_to_context(
            new_key="listboard_url", existing_key=self.listboard_url, context=context
        )
        context = self.add_url_to_context(
            new_key="paginator_url",
            existing_key=self.paginator_url or self.listboard_url,
            context=context,
        )
        return context

    def get_template_names(self):
        return [self.get_template_from_context(self.listboard_template)]

    @property
    def url_kwargs(self):
        """Returns a dictionary of URL options for either the
        Search form URL and the Form Action.
        """
        return {}

    @property
    def listboard_model_cls(self):
        """Returns the listboard's model class.

        Accepts `listboard_model` as a model class or label_lower.
        """
        if not self.listboard_model:
            raise ListboardViewError(
                f"Listboard model not declared. Got None. See {repr(self)}"
            )
        try:
            return django_apps.get_model(self.listboard_model)
        except (ValueError, AttributeError):
            return self.listboard_model

    def get_queryset_exclude_options(self, request, *args, **kwargs):
        """Returns exclude options applied to every
        queryset.
        """
        return {}

    def get_queryset_filter_options(self, request, *args, **kwargs):
        """Returns filter options applied to every
        queryset.
        """
        return {}

    def get_filtered_queryset(self, filter_options=None, exclude_options=None):
        """Returns a queryset, called by `get_queryset`.

        This can be overridden but be sure to use the default_manager.
        """
        return (
            getattr(self.listboard_model_cls, self.listboard_model_manager_name)
            .filter(**filter_options)
            .exclude(**exclude_options)
        )

    def get_queryset(self):
        """Return the queryset for this view.

        Completely overrides ListView.get_queryset.

        Important:

        Passes filter/exclude criteria to `get_filtered_queryset`.

        Note: The returned queryset is set to self.object_list in
        `get()` just before rendering to response.
        """
        filter_options = self.get_queryset_filter_options(
            self.request, *self.args, **self.kwargs
        )
        exclude_options = self.get_queryset_exclude_options(
            self.request, *self.args, **self.kwargs
        )
        queryset = self.get_filtered_queryset(
            filter_options=filter_options, exclude_options=exclude_options
        )
        ordering = self.get_ordering()
        if ordering:
            if isinstance(ordering, six.string_types):
                ordering = (ordering,)
            queryset = queryset.order_by(*ordering)
        return queryset

    def get_wrapped_queryset(self, queryset):
        """Returns a list of wrapped model instances.

        Usually is passed the queryset `object_list` and wraps each
        instance just before passing to the template.
        """
        wrapped_objs = []
        for obj in queryset:
            model_wrapper = self.model_wrapper_cls(obj)
            model_wrapper = self.update_wrapped_instance(model_wrapper)
            wrapped_objs.append(model_wrapper)
        return wrapped_objs

    def update_wrapped_instance(self, model_wrapper):
        """Returns a model_wrapper.

        Hook to add attrs to wrapped model instance.
        """
        return model_wrapper


class ListboardView(
    SiteQuerysetViewMixin,
    QueryStringViewMixin,
    UrlRequestContextMixin,
    SearchListboardMixin,
    ListboardPermmissionMixin,
    BaseListboardView,
):
    pass
