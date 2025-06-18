import io
import os
from concurrent.futures import ThreadPoolExecutor
import uuid
import requests
from PIL import Image
from PyPDF2 import PdfReader
from django.contrib.auth.models import User
from django.core.files.base import ContentFile, File
from django.core.files.storage import default_storage
from django.db import models
from django.db.models.signals import  post_save
from django.dispatch import receiver
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from transformers import BartTokenizer, BartForConditionalGeneration


class Category(models.Model):
    title = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.title

class Product(models.Model):
    user = models.ForeignKey(User, related_name='products', on_delete=models.CASCADE)
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50)
    content = models.FileField(upload_to='products/', default='/Users/maria/Desktop/BetterReads/store/defaultFile.pdf')
    description = models.TextField(blank=True)
    price = models.IntegerField()
    image = models.ImageField(upload_to='uploads/product_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_illustrated = models.BooleanField(default=False)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return self.title

    def get_display_price(self):
        return self.price / 100

    def get_thumbnail(self):
        if self.image:
            return self.image.url
        return 'path/to/default_image.jpg'

    def make_thumbnail(self, image, size=(300, 300)):
        img = Image.open(image)
        img.convert('RGB')
        img.thumbnail(size)

        thumb_io = io.BytesIO()
        img.save(thumb_io, 'JPEG', quality=85)
        name = image.name.replace('uploads/product_images/', '')
        thumbnail = File(thumb_io, name=name)

        return thumbnail

    def generate_summaries(self):
        tokenizer = BartTokenizer.from_pretrained('facebook/bart-large-cnn')
        model = BartForConditionalGeneration.from_pretrained('facebook/bart-large-cnn')

        def generate_summary(page):
            text = page.extract_text()
            inputs = tokenizer(text, return_tensors="pt", max_length=1024, truncation=True)
            summary_ids = model.generate(inputs['input_ids'], num_beams=4, min_length=30, max_length=200,
                                         early_stopping=True)
            summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            return summary

        summaries = []
        with default_storage.open(self.content.name, 'rb') as pdf_file:
            pdf = PdfReader(pdf_file)
            with ThreadPoolExecutor() as executor:
                summaries = list(executor.map(generate_summary, pdf.pages))

        return summaries

    def generate_images_from_prompts(self):
        prompts = self.generate_summaries()
        generated_image_paths = []

        output_folder = "/Users/maria/Desktop/BetterReads/media/uploads/product_images/"

        def generate_image(prompt):
            response = requests.post(
                f"https://api.stability.ai/v2beta/stable-image/generate/sd3",
                headers={
                    "authorization": f"Bearer sk-1K9lrjqjQMyVGXOKwWFcK8ruuHPjDihTR5BaAbpFrNx4k82H",
                    "accept": "image/*"
                },
                files={"none": ''},
                data={
                    "prompt": prompt,
                    "output_format": "jpeg",
                },
            )

            if response.status_code == 200:
                image_filename = f"{uuid.uuid4()}.jpeg"
                image_path = os.path.join(output_folder, image_filename)
                with open(image_path, 'wb') as file:
                    file.write(response.content)
                return image_path
            return None

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(generate_image, prompts))
            generated_image_paths = [result for result in results if result is not None]
        return generated_image_paths

    def illustrate_content(self):
        illustrated_pdf_path = f"products/{self.slug}_illustrated.pdf"
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)

        with default_storage.open(self.content.name, 'rb') as pdf_file:
            pdf = PdfReader(pdf_file)
            images = self.generate_images_from_prompts()
            image_index = 0

            for page_number in range(len(pdf.pages)):
                page = pdf.pages[page_number]
                text = page.extract_text()
                page_width, page_height = page.mediabox[2], page.mediabox[3]
                lines = text.split('\n')
                y_start = page_height - 100
                font_size = 15

                for line in lines:
                    text_width = c.stringWidth(line)
                    x_coordinate = (page_width - text_width) / 2
                    c.setFont("Helvetica", font_size)
                    c.drawString(x_coordinate, y_start, line)
                    y_start -= 1.5 * font_size

                if (page_number + 1) % 2 == 0 and image_index < len(images):
                    image_path = images[image_index]
                    image_index += 1
                    c.drawImage(image_path, 0, 0, width=page_width, height=page_height)

                c.showPage()

        c.save()

        with default_storage.open(illustrated_pdf_path, 'wb') as pdf_output:
            pdf_output.write(buffer.getvalue())

        return illustrated_pdf_path




@receiver(post_save, sender=Product)
def post_save_product_handler(sender, instance, created, **kwargs):
    if created and instance.content and instance.is_illustrated:
        illustrated_pdf_path = instance.illustrate_content()
        instance.content.save(illustrated_pdf_path, ContentFile(default_storage.open(illustrated_pdf_path).read()))
        instance.save(update_fields=['content'])

class Order(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    paid_amount = models.IntegerField(blank=True, null=True)
    is_paid = models.BooleanField(default=False)
    payment_intent = models.CharField(max_length=255, null=True)
    created_by = models.ForeignKey(User, related_name='orders', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='items', on_delete=models.CASCADE)
    price = models.IntegerField()
    quantity = models.IntegerField(default=1)

class Purchase(models.Model):
    user = models.ForeignKey(User, related_name='purchased_products', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='purchased_by', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    purchase_date = models.DateTimeField(auto_now_add=True)

class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(blank=True, null=True)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
