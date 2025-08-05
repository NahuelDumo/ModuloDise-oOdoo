# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class DesignRechazoWizard(models.TransientModel):
    _name = 'design.rechazo.wizard'
    _description = 'Wizard para rechazar un diseño'

    design_id = fields.Many2one('design.design', string='Diseño', required=True, readonly=True)
    motivo = fields.Text(string='Motivo del Rechazo', required=True)
    
    def action_confirmar_rechazo(self):
        """Confirma el rechazo del diseño con el motivo proporcionado."""
        self.ensure_one()
        if not self.motivo.strip():
            raise ValidationError(_("Debe proporcionar un motivo para el rechazo."))
            
        # Llamar al método de rechazo en el modelo de diseño
        self.design_id.marcar_como_rechazado(self.motivo)
        
        # Cerrar el wizard
        return {'type': 'ir.actions.act_window_close'}
