from django import forms

from .models import Product, Order

# forms.py
from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'inline-block py-2 px-4 bg-white text-black rounded-full border border-black border-2',
                'rows': 1,
                'cols': 20,
            }),
        }

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('first_name', 'last_name')

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ('category', 'title', 'content', 'description', 'price', 'image','is_illustrated')
        widgets = {
            'category': forms.Select(attrs={
                'class': 'w-full p-4 border border-gray-200'
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full p-4 border border-gray-200'
            }),
            'content': forms.FileInput(attrs={
                'class': 'w-full p-4 border border-gray-200'
            }),
            'is_illustrated': forms.CheckboxInput(attrs={
                'class': 'w-full p-4 border border-gray-200'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full p-4 border border-gray-200'
            }),
            'price': forms.TextInput(attrs={
                'class': 'w-full p-4 border border-gray-200'
            }),
            'image': forms.FileInput(attrs={
                'class': 'w-full p-4 border border-gray-200'
            })
        }