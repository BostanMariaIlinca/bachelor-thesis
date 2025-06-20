from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils.text import slugify
from store.forms import ProductForm
from store.models import Product
from .models import Userprofile


def vendor_detail(request, pk):
    user = User.objects.get(pk=pk)

    return render(request, 'userprofile/vendor_detail.html', {
        'user': user
    })


def myaccount(request):
    return render(request, 'userprofile/myaccount.html')


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()

            login(request, user)

            userprofile = Userprofile.objects.create(user=user)

            return redirect('frontpage')
    else:
        form = UserCreationForm()

    return render(request, 'userprofile/signup.html', {
        'form': form
    })


@login_required
def my_store(request):
    products = Product.objects.filter(user=request.user)
    context = {
        'products': products,
    }
    return render(request, 'userprofile/my_store.html', context)

@login_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)

        if form.is_valid():
            title = request.POST.get('title')

            product = form.save(commit=False)
            product.user = request.user
            product.slug = slugify(title)
            product.save()

            messages.success(request, 'The book was added!')

            return redirect('my_store')
    else:
        form = ProductForm()

    return render(request, 'userprofile/product_form.html', {
        'title': 'Add book',
        'form': form
    })


@login_required
def edit_product(request, pk):
    product = Product.objects.filter(user=request.user).get(pk=pk)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)

        if form.is_valid():
            form.save()

            messages.success(request, 'The changes were saved!')

            return redirect('my_store')
    else:
        form = ProductForm(instance=product)

    return render(request, 'userprofile/product_form.html', {
        'title': 'Edit book',
        'product': product,
        'form': form
    })


@login_required
def delete_product(request, pk):
    product = Product.objects.filter(user=request.user).get(pk=pk)
    #product.status = Product.DELETED
    #product.save()
    product.delete()

    messages.success(request, 'The book was deleted!')

    return redirect('my_store')


@login_required
def myaccount(request):
    return render(request, 'userprofile/myaccount.html')


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()

            login(request, user)

            userprofile = Userprofile.objects.create(user=user)

            return redirect('frontpage')
    else:
        form = UserCreationForm()


    return render(request, 'userprofile/signup.html', {
        'form': form
    })

