from odoo import models, fields, api, _
from odoo.exceptions import UserError

class DesignDeleteConfirm(models.TransientModel):
    _name = 'design.delete.confirm'
    _description = 'Confirmar eliminación de diseños'
    
    design_ids = fields.Many2many('design.design', string='Diseños a eliminar')
    count = fields.Integer('Número de diseños a eliminar', readonly=True)
    
    @api.model
    def default_get(self, fields):
        res = super(DesignDeleteConfirm, self).default_get(fields)
        if self._context.get('default_design_ids'):
            res['design_ids'] = [(6, 0, self._context.get('default_design_ids'))]
            res['count'] = self._context.get('default_count', 0)
        return res
    
    def action_confirm(self):
        """Elimina los diseños seleccionados"""
        self.ensure_one()
        if not self.design_ids:
            raise UserError(_("No hay diseños para eliminar."))
            
        # Verificar permisos
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_("Solo los administradores pueden eliminar diseños."))
            
        # Eliminar los diseños
        self.design_ids.unlink()
        
        # Mensaje de confirmación
        message = _("Se han eliminado %s diseños correctamente.", len(self.design_ids))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
