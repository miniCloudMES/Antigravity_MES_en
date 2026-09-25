from django import forms
from .models import LibraryFile, FileCategory


class LibraryFileForm(forms.ModelForm):
    class Meta:
        model = LibraryFile
        fields = ['category', 'title', 'file', 'description']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter file title'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description (optional)'}),
        }
        labels = {
            'category': 'Category',
            'title': 'File Name',
            'file': 'Choose File',
            'description': 'Description',
        }


class FileCategoryForm(forms.ModelForm):
    class Meta:
        model = FileCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter category name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Category description (optional)'}),
        }
        labels = {
            'name': 'Category Name',
            'description': 'Category Description',
        }
