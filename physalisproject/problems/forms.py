from django import forms
from django_svg_image_form_field import SvgAndImageFormField

from .models import Image


class ImageForm(forms.ModelForm):
    class Meta:
        model = Image
        exclude = []
        field_classes = {
            'path_to_image': SvgAndImageFormField,
        }
