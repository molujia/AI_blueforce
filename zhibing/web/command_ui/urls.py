from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("tiles/<int:z>/<int:x>/<int:y>.png", views.serve_tile, name="serve_tile"),
    path("api/command", views.command, name="command"),
    path("api/demo-scene", views.demo_scene, name="demo_scene"),
    path("api/session/reset", views.reset_session, name="reset_session"),
    path("api/route-constraint", views.route_constraint, name="route_constraint"),
]