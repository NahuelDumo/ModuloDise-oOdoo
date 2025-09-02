# -*- coding: utf-8 -*-
from odoo import models, fields

class PortalAccessWizard(models.TransientModel):
    """Modelo stub temporal para resolver referencias huérfanas"""
    _name = 'portal.access.wizard'
    _description = 'Portal Access Wizard (Deprecated)'
    
    # Campos mínimos para evitar errores
    name = fields.Char('Name', default='Deprecated')
    
    def action_confirm(self):
        """Método dummy para compatibilidad"""
        return {'type': 'ir.actions.act_window_close'}
