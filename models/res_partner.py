# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # is_design_user = fields.Boolean(
    #     string='Usuario Diseño',
    #     default=False,
    #     help='Si está marcado, el usuario será redirigido automáticamente a /my/designs en el portal'
    # )

    # def toggle_design_user(self):
    #     """Alterna el estado de Usuario Diseño"""
    #     for record in self:
    #         record.is_design_user = not record.is_design_user
    #     return True
