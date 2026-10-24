from django.contrib import admin

from .models import Portfolio, PortfolioItem


class PortfolioItemInline(admin.TabularInline):
    model = PortfolioItem
    extra = 0


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('student', 'title', 'visibility', 'share_slug', 'updated_at')
    list_filter = ('visibility',)
    search_fields = ('student__username', 'title')


@admin.register(PortfolioItem)
class PortfolioItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'portfolio', 'item_type', 'is_featured', 'position')
    list_filter = ('item_type', 'is_featured')
    search_fields = ('title', 'portfolio__student__username')
