from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError

class DesignRechazoWizard(models.TransientModel):
    _name = 'design.rechazo.wizard'  # Cambiado para coincidir con la vista
    _description = 'Wizard para rechazar diseños'

    design_id = fields.Many2one('design.design', string='Diseño', required=True)
    motivo = fields.Text('Motivo del rechazo', required=True, 
                        help='Explique las razones por las que rechaza este diseño')
    
    @api.model
    def default_get(self, fields):
        """Establecer valores por defecto del contexto"""
        res = super().default_get(fields)
        # Obtener design_id del contexto activo
        active_id = self._context.get('active_id')
        default_design_id = self._context.get('default_design_id')
        
        if default_design_id:
            res['design_id'] = default_design_id
        elif active_id and self._context.get('active_model') == 'design.design':
            res['design_id'] = active_id
            
        return res
    
    def action_confirmar_rechazo(self):  # Cambiado para coincidir con la vista
        """Ejecuta el rechazo del diseño"""
        self.ensure_one()
        
        # Verificar permisos
        if not self.env.user.has_group('ModuloDisenoOdoo.group_validador'):
            raise AccessError(_("Solo los validadores pueden rechazar diseños."))
        
        # Verificar que el diseño existe y está en estado válido
        if not self.design_id:
            raise UserError(_("No se ha seleccionado un diseño válido."))
        
        # Verificar que el motivo no esté vacío
        if not self.motivo or not self.motivo.strip():
            raise UserError(_("Debe proporcionar un motivo para el rechazo."))
            
        if self.design_id.state not in ['validacion', 'cliente']:
            raise UserError(_("El diseño no está en un estado que permita el rechazo."))
        
        # Llamar al método de rechazo del diseño
        self.design_id.marcar_como_rechazado(self.motivo)
        
        return {
            'type': 'ir.actions.act_window_close',
        }