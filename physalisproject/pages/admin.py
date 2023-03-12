from django.contrib import admin
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site

admin.site.unregister(FlatPage)


@admin.register(FlatPage)
class FlatPageAdmin(admin.ModelAdmin):
    fields = ('url', 'title', 'content', 'template_name',)
    view_on_site = False

    def save_model(self, request, obj, form, change):
        if not obj.sites:
            obj.sites = Site.objects.get_current()
        super().save_model(
            request=request,
            obj=obj,
            form=form,
            change=change
        )
