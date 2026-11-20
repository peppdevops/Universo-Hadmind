"""Ajustes de django-allauth para HADMIND."""

from allauth.account.adapter import DefaultAccountAdapter


class AdaptadorCuenta(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        # Nadie se registra solo: las cuentas del equipo las crea el
        # superusuario en Equipo → Usuarios.
        return False
