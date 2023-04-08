from django.contrib import admin
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site

admin.site.unregister(FlatPage)


@admin.register(FlatPage)
class FlatPageAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('url', 'title', 'content', 'template_name',)}),
        (('Сайты'), {
            'classes': ('collapse',),
            'fields': (
                'sites',
            ),
        }),
    )

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == 'sites':
            kwargs['initial'] = [Site.objects.get_current()]
        return super(FlatPageAdmin, self).formfield_for_foreignkey(db_field,
                                                                   request,
                                                                   **kwargs)
