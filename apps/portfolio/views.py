from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.crypto import get_random_string
from django.views.decorators.http import require_POST

from apps.courses.analytics import published_latest_grades
from apps.users.roles import is_student

from .models import Portfolio, PortfolioItem


@login_required(login_url='login')
def my_portfolio(request):
    if not is_student(request.user):
        messages.info(request, 'Portfolios are designed for students.')
        return redirect('dashboard')

    portfolio, _ = Portfolio.objects.get_or_create(student=request.user)
    items = portfolio.items.select_related('grade__submission__assignment').all()
    published = published_latest_grades(student=request.user)
    return render(
        request,
        'portfolio/my_portfolio.html',
        {'portfolio': portfolio, 'items': items, 'published': published},
    )


@login_required(login_url='login')
@require_POST
def toggle_visibility(request):
    if not is_student(request.user):
        messages.error(request, 'Only students can manage their portfolios.')
        return redirect('dashboard')
    portfolio, _ = Portfolio.objects.get_or_create(student=request.user)
    portfolio.visibility = (
        Portfolio.VISIBILITY_PUBLIC
        if portfolio.visibility != Portfolio.VISIBILITY_PUBLIC
        else Portfolio.VISIBILITY_CLASS
    )
    if not portfolio.share_slug:
        portfolio.share_slug = get_random_string(12)
    portfolio.save()
    messages.success(request, f'Portfolio visibility set to {portfolio.get_visibility_display()}.')
    return redirect('portfolio:my_portfolio')


@login_required(login_url='login')
@require_POST
def add_from_grade(request, grade_pk):
    if not is_student(request.user):
        messages.error(request, 'Only students can add items to their portfolios.')
        return redirect('dashboard')

    from apps.courses.models import Grade

    grade = get_object_or_404(
        Grade.objects.select_related('submission__assignment'),
        pk=grade_pk,
        submission__student=request.user,
        is_published=True,
    )
    portfolio, _ = Portfolio.objects.get_or_create(student=request.user)
    if portfolio.items.filter(grade=grade).exists():
        messages.info(request, 'That published assignment is already in your portfolio.')
        return redirect('portfolio:my_portfolio')

    title = f"{grade.submission.assignment.title} ({grade.submission.assignment.course.code})"
    description = grade.submission.assignment.description or ''
    skills = grade.submission.assignment.category.replace('_', ' ').title()
    PortfolioItem.objects.create(
        portfolio=portfolio,
        grade=grade,
        item_type=PortfolioItem.ITEM_ASSIGNMENT,
        title=title,
        description=description,
        skills=skills,
    )
    messages.success(request, 'Published assignment added to your portfolio.')
    return redirect('portfolio:my_portfolio')


@login_required(login_url='login')
@require_POST
def feature_toggle(request, pk):
    if not is_student(request.user):
        messages.error(request, 'Only students can manage their portfolios.')
        return redirect('dashboard')
    item = get_object_or_404(PortfolioItem, pk=pk, portfolio__student=request.user)
    item.is_featured = not item.is_featured
    item.save(update_fields=['is_featured', 'updated_at'])
    messages.success(request, 'Portfolio item updated.')
    return redirect('portfolio:my_portfolio')
