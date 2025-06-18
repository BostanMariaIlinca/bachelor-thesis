from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from .cart import Cart
from .forms import OrderForm, ReviewForm
from .models import Category, Product, OrderItem, Purchase, Order
import json
import stripe
from django.http import JsonResponse, HttpResponseRedirect


def search(request):
    query = request.GET.get('query', '')
    products = Product.objects.filter(Q(title__icontains=query) | Q(description__icontains=query))

    return render(request, 'store/search.html', {
        'query': query,
        'products': products,
    })

def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = category.products.all()

    return render(request, 'store/category_detail.html', {
        'category': category,
        'products': products
    })


def purchased_product_detail(request, category_slug, slug):
    product = get_object_or_404(Product, slug=slug)
    is_owner = product.user_id == request.user.id

    return render(request, 'store/purchased_product_detail.html', {
        'product': product,
        'current_user': request.user,
        'is_owner': is_owner
    })


@login_required
def product_detail(request, category_slug, slug):
    product = get_object_or_404(Product, category__slug=category_slug, slug=slug)
    is_owner = product.user_id == request.user.id
    user_has_purchased = Purchase.objects.filter(user=request.user, product=product).exists()

    # Retrieve all reviews for the product
    reviews = product.reviews.all()

    paginator = Paginator(reviews, 2)  # 2 reviews per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, 'Your review has been submitted.')
            return redirect('product_detail', category_slug=product.category.slug, slug=product.slug)
    else:
        form = ReviewForm()

    return render(request, 'store/product_detail.html', {
        'product': product,
        'current_user': request.user,
        'is_owner': is_owner,
        'user_has_purchased': user_has_purchased,
        'form': form,
        'reviews': page_obj,
        'is_paginated': True if paginator.num_pages > 1 else False,
    })



def add_to_cart(request, product_id):
    cart = Cart(request)
    cart.add(product_id)

    return redirect('cart_view')


def change_quantity(request, product_id):
    action = request.GET.get('action', '')

    if action:
        quantity = 1

        if action == 'decrease':
            quantity = -1

        cart = Cart(request)
        cart.add(product_id, quantity, True)

    return redirect('cart_view')


def remove_from_cart(request, product_id):
    cart = Cart(request)
    cart.remove(product_id)

    return redirect('cart_view')


def cart_view(request):
    cart = Cart(request)

    return render(request, 'store/cart_view.html', {
        'cart': cart
    })


@login_required
def checkout(request):
    cart = Cart(request)

    if cart.get_total_cost() == 0:
        return redirect('cart_view')

    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                request_body = request.body.decode('utf-8')
                data = json.loads(request_body)
            else:
                data = request.POST
        except json.JSONDecodeError as e:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        form = OrderForm(data)

        if form.is_valid():
            total_price = 0
            items = []

            for item in cart:
                product = item['product']
                total_price += product.price * int(item['quantity'])

                items.append({
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': product.title,
                        },
                        'unit_amount': int(product.price * 100)  # Stripe expects the amount in cents
                    },
                    'quantity': int(item['quantity'])
                })

            stripe.api_key = settings.STRIPE_SECRET_KEY
            try:
                session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=items,
                    mode='payment',
                    success_url='http://localhost:8000/cart/success/',
                    cancel_url='http://localhost:8000/cart/',
                )
                payment_intent = session.payment_intent

                order = Order.objects.create(
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    created_by=request.user,
                    is_paid=True,
                    payment_intent=payment_intent,
                    paid_amount=total_price
                )

                for item in cart:
                    product = item['product']
                    quantity = int(item['quantity'])
                    price = product.price * quantity

                    OrderItem.objects.create(order=order, product=product, price=price, quantity=quantity)

                    # Add purchased products to the user's library
                    Purchase.objects.create(
                        user=request.user,
                        product=product,
                        quantity=quantity
                    )

                cart.clear()

                # Redirect to Stripe Checkout URL
                return HttpResponseRedirect(session.url)
            except stripe.error.StripeError as e:
                return JsonResponse({'error': str(e)}, status=400)

        else:
            return JsonResponse({'error': form.errors}, status=400)

    else:
        form = OrderForm()

    return render(request, 'store/checkout.html', {
        'cart': cart,
        'form': form,
        'pub_key': settings.STRIPE_PUB_KEY,
    })
def success(request):
    return render(request, 'store/success.html')