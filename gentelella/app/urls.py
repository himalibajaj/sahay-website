from django.urls import path, re_path
from app import views

urlpatterns = [
    # Matches any html file - to be used for gentella
    # Avoid using your .html in your resources.
    # Or create a separate django app.
    path('get_chat_response_ajax', views.get_chat_response_ajax, name='get_chat_response_ajax'),
    path('courtdetails.html', views.courtdetails, name='courtdetails'),
    path('reports.html', views.reports, name='reports'),
    path('year_2025.html', views.year_2025, name='reports'),
    path('year_2024.html', views.year_2024, name='reports'),
    path('year_2023.html', views.year_2023, name='reports'),
    path('year_2022.html', views.year_2022, name='reports'),
    path('year_2021.html', views.year_2021, name='reports'),
    path('year_2020.html', views.year_2020, name='reports'),
    path('year_2019.html', views.year_2019, name='reports'),
    path('year_2018.html', views.year_2018, name='reports'),
    path('year_2017.html', views.year_2017, name='reports'),
    path('year_2016.html', views.year_2016, name='reports'),
    path('year_2015.html', views.year_2015, name='reports'),
    

    re_path(r'^.*\.html', views.gentella_html, name='gentella'),

    # The home page
    path('', views.index, name='index'),
]
