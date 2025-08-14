# modulo_diseno/models/revision_log.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class RevisionLog(models.Model):
    _name = "design.revision_log"
    _description = "Historial de revisiones del diseño"
    _order = "create_date desc"
    _inherit = ['mail.thread']
    
    # Hacer que el registro sea inmutable
    _disallowed_fields_to_discard = {
        'message_last_post', 'message_attachment_count', 'message_has_error', 'message_has_error_counter',
        'message_has_sms_error', 'message_is_follower', 'message_main_attachment_id', 'message_needaction',
        'message_needaction_counter', 'message_needaction_emoji', 'message_has_error_counter', 'message_has_error',
        'message_has_sms_error', 'message_needaction_counter', 'message_needaction', 'message_unread',
        'message_unread_counter', 'website_message_ids', 'message_follower_ids', 'activity_ids', 'activity_state',
        'activity_user_id', 'activity_type_id', 'activity_date_deadline', 'my_activity_date_deadline',
        'activity_summary', 'activity_exception_decoration', 'activity_exception_icon'
    }

    design_id = fields.Many2one("design.design", string="Diseño relacionado", ondelete="cascade", required=True)
    usuario_id = fields.Many2one("res.users", string="Usuario", required=True)
    observaciones = fields.Text("Observaciones")
    tipo = fields.Selection([
        ('creacion', 'Creación'),
        ('validacion_disenador', 'Validación Diseñador'),
        ('validacion_validador', 'Validación Validador'),
        ('rechazo', 'Rechazo'),
        ('aprobacion_cliente', 'Aprobación del Cliente'),
        ('cambio_estado', 'Cambio de Estado'),
        ('actualizacion', 'Actualización'),
        ('comentario', 'Comentario')
    ], string="Tipo de acción", required=True, tracking=True)
    
    # Campos de solo lectura
    create_date = fields.Datetime(string='Fecha de creación', readonly=True, tracking=True)
    create_uid = fields.Many2one('res.users', string='Creado por', readonly=True)
    
    # Restringir eliminación de registros
    def unlink(self):
        raise UserError(_("No se pueden eliminar registros del historial de revisiones."))
    
    # Restringir modificación de registros
    def write(self, vals):
        # Permitir solo campos de seguimiento y mensajes
        allowed_fields = self._disallowed_fields_to_discard | {'message_ids', 'activity_ids'}
        if any(field not in allowed_fields for field in vals.keys()):
            raise UserError(_("No se pueden modificar los registros del historial de revisiones."))
        return super(RevisionLog, self).write(vals)
    
    @api.model
    def create(self, vals):
        # Asegurar que se registre el usuario que crea el registro
        if 'usuario_id' not in vals and 'usuario_id' not in self._context:
            vals['usuario_id'] = self.env.user.id
        return super(RevisionLog, self).create(vals)
