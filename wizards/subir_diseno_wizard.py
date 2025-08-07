from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SubirDisenoWizard(models.TransientModel):
    _name = 'design.subir.diseno.wizard'
    _description = 'Wizard para subir nuevo diseño'
    
    design_id = fields.Many2one('design.design', string='Diseño', required=True)
    image = fields.Binary(string='Nuevo diseño', required=True)
    
    def action_subir_diseno(self):
        self.ensure_one()
        
        if not self.image:
            raise ValidationError(_("Debe seleccionar una imagen para continuar."))
            
        # Actualizar el diseño con la nueva imagen
        self.design_id.write({
            'image': self.image,
            'diseño_subido': True,
            'fecha_subida_diseno': fields.Datetime.now(),
            'state': 'validacion',
            'rechazado': False,
            'observaciones_rechazo': False,
            'etapa': 'etapa1'
        })
        
        # Registrar en el historial
        self.env['design.revision_log'].create({
            'design_id': self.design_id.id,
            'tipo': 'resubida',
            'observaciones': 'Nueva versión del diseño subida después de rechazo.'
        })
        
        # Notificar a los validadores
        self.design_id.message_post(
            body=_("""
            <p>Se ha subido una nueva versión del diseño después de un rechazo.</p>
            <p>Por favor, revise el nuevo diseño.</p>
            """),
            subject=_("Nueva versión de diseño subida para revisión"),
            partner_ids=[user.partner_id.id for user in self.env.ref('ModuloDisenoOdoo.group_validador').users]
        )
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'design.design',
            'view_mode': 'form',
            'res_id': self.design_id.id,
            'target': 'current',
            'flags': {'form': {'action_buttons_to_top': True}}
        }
