from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime

class Design(models.Model):
    _name = "design.design"
    _description = "Diseño"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "create_date desc"
    
    # Lista de campos que se pueden editar después de subir el diseño
    _fields_editables_after_upload = [
        'checklist_ids', 'comentario_validador', 'comentario_disenador',
        'visible_para_cliente', 'aprobado_cliente', 'rechazado', 'observaciones_rechazo'
    ]

    name = fields.Char("Nombre del diseño", required=True, tracking=True)
    image = fields.Binary("Diseño (imagen)")
    cliente_id = fields.Many2one("res.partner", string="Cliente", required=True, tracking=True)
    task_id = fields.Many2one("project.task", string="Tarea asociada", tracking=True)

    categoria_id = fields.Many2one("product.category", string="Categoría de producto", required=True)

    etapa = fields.Selection([
        ('etapa1', 'Etapa 1'),
        ('etapa2', 'Etapa 2'),
        ('completo', 'Completado')
    ], string="Etapa actual", default='etapa1', tracking=True)

    checklist_ids = fields.One2many("design.checklist_item", "design_id", string="Checklist")

    visible_para_cliente = fields.Boolean("Visible al cliente", default=False, tracking=True)
    aprobado_cliente = fields.Boolean("Aprobado por el cliente", default=False, tracking=True)

    rechazado = fields.Boolean("Rechazado", default=False, tracking=True)
    observaciones_rechazo = fields.Text("Observaciones de rechazo")

    historial_ids = fields.One2many("design.revision_log", "design_id", string="Historial de validaciones")

    fecha_aprobacion_cliente = fields.Datetime("Fecha de aprobación del cliente", readonly=True)
    fecha_rechazo = fields.Datetime("Fecha de rechazo", readonly=True)

    state = fields.Selection([
        ('borrador', 'Borrador'),
        ('validacion', 'Esperando validación'),
        ('cliente', 'Esperando cliente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
    ], string="Estado", default='borrador', tracking=True)
    
    # Campos para control de estado
    diseño_subido = fields.Boolean(string='Diseño subido', default=False, copy=False)
    fecha_subida_diseno = fields.Datetime(string='Fecha de subida', copy=False, readonly=True)
    can_reject = fields.Boolean(string='Puede ser rechazado', compute='_compute_can_reject', store=False)
    
    # Campos de comentarios
    comentario_validador = fields.Text("Comentarios del validador", 
                                     help="Comentarios del validador sobre el diseño",
                                     tracking=True)
    comentario_disenador = fields.Text("Comentarios del diseñador", 
                                      help="Comentarios del diseñador sobre el diseño",
                                      tracking=True)

    @api.depends('checklist_ids.validado_por_disenador', 'checklist_ids.validado_por_validador')
    def _compute_estado_checklist(self):
        for record in self:
            checklist = record.checklist_ids
            completo_disenador = checklist and all(item.validado_por_disenador for item in checklist)
            completo_validador = checklist and all(item.validado_por_validador for item in checklist)

            if completo_disenador and record.state == 'borrador':
                record.state = 'validacion'
                record.message_post(body="Checklist completado por el diseñador. Esperando validación del validador.")
                record._notificar_a_validadores()

            if completo_disenador and completo_validador and record.etapa == 'etapa1':
                record.state = 'cliente'
                record.etapa = 'etapa2'
                record.visible_para_cliente = True
                record.message_post(body="Checklist validado por el validador. Avanzando a Etapa 2.")
                record._notificar_a_disenador()

    def _notificar_a_validadores(self):
        validadores = self.env.ref('modulo_diseno.group_validador').users
        template = self.env.ref('modulo_diseno.email_template_diseño_pendiente_validar')
        for validador in validadores:
            template.send_mail(self.id, force_send=True, email_values={'email_to': validador.email})

    def _notificar_a_disenador(self):
        template = self.env.ref('modulo_diseno.email_template_diseño_validado')
        template.send_mail(self.id, force_send=True, email_values={'email_to': self.create_uid.email})

    def action_rechazar_diseno(self):
        """Abre un wizard para que el validador ingrese los motivos del rechazo."""
        self.ensure_one()
        
        # Verificar permisos
        if not self.env.user.has_group('modulo_diseno.group_validador') and not self.env.user.has_group('base.group_system'):
            raise AccessError(_("Solo los validadores pueden rechazar diseños."))
            
        # Verificar que el diseño esté en un estado que permita el rechazo
        if self.state not in ['en_revision', 'por_validar']:
            raise UserError(_("No se puede rechazar un diseño en el estado actual."))
            
        return {
            'name': _('Rechazar Diseño'),
            'type': 'ir.actions.act_window',
            'res_model': 'design.rechazo.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_design_id': self.id,
                'default_motivo': self.observaciones_rechazo or '',
            }
        }
        
    def marcar_como_rechazado(self, motivo):
        """Marca el diseño como rechazado con el motivo proporcionado."""
        for record in self:
            record.rechazado = True
            record.observaciones_rechazo = motivo
            record.fecha_rechazo = fields.Datetime.now()
            record.visible_para_cliente = False
            record.aprobado_cliente = False
            record.etapa = 'etapa1'
            record.state = 'rechazado'
            record.diseño_subido = False  # Permitir ediciones nuevamente
            
            # Registrar en el historial
            self.env['design.revision_log'].create({
                'design_id': record.id,
                'tipo': 'rechazo',
                'observaciones': f'Diseño rechazado. Motivo: {motivo}'
            })
            
            # Enviar notificación de rechazo al diseñador
            template = self.env.ref('modulo_diseno.email_template_diseno_rechazado')
            if template:
                template.with_context(
                    lang=self.env.user.lang,
                    user_name=self.env.user.name,
                ).send_mail(record.id, force_send=True, email_values=None)
            
            record.message_post(
                body=_(f"Diseño rechazado. Motivo: {motivo}"),
                subject=_("Diseño Rechazado")
            )
        return True

        self.env['design.revision_log'].create({
            'design_id': self.id,
            'usuario_id': self.env.user.id,
            'observaciones': observacion,
            'tipo': 'rechazo',
        })

    def marcar_como_aprobado_por_cliente(self):
        self.aprobado_cliente = True
        self.fecha_aprobacion_cliente = fields.Datetime.now()
        self.etapa = 'etapa2'
        self.state = 'aprobado'

        # Registrar en el historial
        self.env['design.revision_log'].create({
            'design_id': self.id,
            'usuario_id': self.env.user.id,
            'observaciones': 'Aprobado por cliente',
            'tipo': 'aprobacion_cliente',
        })

    @api.model
    def create(self, vals):
        # Asegurar que se establezca el usuario creador si no se proporciona
        if 'user_id' not in vals and 'user_id' not in self._context and self.env.uid:
            vals['user_id'] = self.env.uid
            
        # Crear el registro
        record = super(Design, self).create(vals)
        
        # Registrar en el historial
        self.env['design.revision_log'].create({
            'design_id': record.id,
            'usuario_id': self.env.uid,
            'tipo': 'creacion',
            'observaciones': 'Diseño creado y listo para comenzar.'
        })
        
        # Enviar notificación al diseñador si corresponde
        if record.user_id and record.user_id.email:
            template = self.env.ref('modulo_diseno.email_template_diseno_creado', raise_if_not_found=False)
            if template:
                template.with_context(
                    lang=record.user_id.lang,
                    user_name=record.user_id.name,
                ).send_mail(record.id, force_send=True, email_values=None)
        
        categoria_id = vals.get('categoria_id')
        if not categoria_id:
            return record

        plantilla = self.env['design.checklist_template'].search([
            ('categoria_id', '=', categoria_id),
            ('etapa', '=', 'etapa1')
        ], limit=1)

        if plantilla:
            for item in plantilla.item_ids.sorted(key=lambda x: x.orden):
                self.env['design.checklist_item'].create({
                    'name': item.name,
                    'design_id': record.id,
                    'comentario': item.comentario_default or '',
                })

        return record

    @api.depends('state', 'diseño_subido')
    def _compute_can_reject(self):
        """Determina si el diseño puede ser rechazado."""
        for record in self:
            # Solo puede ser rechazado si está en estado de validación y ha sido subido
            record.can_reject = record.state == 'validacion' and record.diseño_subido

    def _check_checklist_completo(self):
        """Verifica si el checklist está completo."""
        self.ensure_one()
        if not self.checklist_ids:
            return False
        # Verificar que todos los ítems estén validados por el diseñador
        return all(item.validado_por_disenador for item in self.checklist_ids)

    def _enviar_notificacion_checklist_completo(self):
        """Envía notificación cuando el checklist está completo."""
        template = self.env.ref('modulolistasdeverificacion.modulolistasdeverificacion_email_template_checklist_completado')
        for record in self:
            if template and record._check_checklist_completo():
                template.with_context(
                    lang=self.env.user.lang,
                    user_name=self.env.user.name,
                ).send_mail(record.id, force_send=True, email_values=None)
                
                # Registrar en el historial
                self.env['design.revision_log'].create({
                    'design_id': record.id,
                    'tipo': 'notificacion',
                    'observaciones': 'Notificación enviada: Checklist completado y listo para validación.'
                })

    def write(self, vals):
        # Verificar si se están modificando campos protegidos después de subir el diseño
        if any(record.diseño_subido for record in self):
            # Filtrar solo los campos editables
            protected_fields = set(vals.keys()) - set(self._fields_editables_after_upload)
            if protected_fields:
                # Verificar si el usuario es administrador o validador
                is_validador = self.env.user.has_group('modulo_diseno.group_validador')
                is_admin = self.env.user.has_group('base.group_system')
                
                if not (is_validador or is_admin):
                    raise UserError(_("No puede modificar los datos del diseño después de haber sido subido. "
                                    "Solo se pueden editar los checklists y comentarios."))
        
        # Verificar si se están actualizando los checklists
        checklist_actualizado = False
        if 'checklist_ids' in vals:
            checklist_actualizado = True
        
        # Registrar cambios en el historial si es necesario
        if 'state' in vals:
            for record in self:
                self.env['design.revision_log'].create({
                    'design_id': record.id,
                    'tipo': 'cambio_estado',
                    'observaciones': f'Estado cambiado de {record.state} a {vals["state"]}'
                })
                
        # Registrar cambios en comentarios
        if 'comentario_validador' in vals or 'comentario_disenador' in vals:
            for record in self:
                if 'comentario_validador' in vals and record.comentario_validador != vals['comentario_validador']:
                    self.env['design.revision_log'].create({
                        'design_id': record.id,
                        'tipo': 'comentario',
                        'observaciones': f'Comentario del validador actualizado: {vals["comentario_validador"]}'
                    })
                if 'comentario_disenador' in vals and record.comentario_disenador != vals['comentario_disenador']:
                    self.env['design.revision_log'].create({
                        'design_id': record.id,
                        'tipo': 'comentario',
                        'observaciones': f'Comentario del diseñador actualizado: {vals["comentario_disenador"]}'
                    })
        
        # Guardar cambios
        result = super(Design, self).write(vals)
        
        # Verificar si se completó el checklist después de la actualización
        if checklist_actualizado:
            for record in self:
                if record._check_checklist_completo() and not record.diseño_subido:
                    record._enviar_notificacion_checklist_completo()
        
        return result

        for record in self:
            if 'etapa' in vals and vals['etapa'] == 'etapa2':
                if not any(item for item in record.checklist_ids if item.name and 'etapa2' in item.name.lower()):
                    plantilla = self.env['design.checklist_template'].search([
                        ('categoria_id', '=', record.categoria_id.id),
                        ('etapa', '=', 'etapa2')
                    ], limit=1)

                    if plantilla:
                        for item in plantilla.item_ids.sorted(key=lambda x: x.orden):
                            self.env['design.checklist_item'].create({
                                'name': item.name,
                                'design_id': record.id,
                                'comentario': item.comentario_default or '',
                            })

        return result

    def abrir_wizard_rechazo(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'design.wizard_rechazo',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_design_id': self.id
            }
        }


    def get_validators_emails(self):
        group = self.env.ref('modulo_diseno.group_validador')
        return ','.join(user.partner_id.email for user in group.users if user.partner_id.email)

    def get_disenador_email(self):
        # Busca el diseñador como quien validó al principio
        disenador = self.checklist_ids.filtered(lambda i: i.usuario_disenador)
        if disenador:
            return disenador[0].usuario_disenador.partner_id.email
        return self.env.user.partner_id.email  # fallback

    def subir_diseno(self):
        """Marca el diseño como subido y congela los datos."""
        for record in self:
            if not record.image:
                raise ValidationError("No puede marcar el diseño como subido sin una imagen.")
            
            # Verificar si el checklist está completo
            if not record._check_checklist_completo():
                raise ValidationError("No puede subir el diseño sin completar todos los items del checklist.")
                
            record.diseño_subido = True
            record.fecha_subida_diseno = fields.Datetime.now()
            
            # Registrar en el historial
            self.env['design.revision_log'].create({
                'design_id': record.id,
                'tipo': 'cambio_estado',
                'observaciones': 'Diseño subido. Los datos del diseño ahora son de solo lectura.'
            })
            
            # Enviar notificación al validador
            template = self.env.ref('modulo_diseno.email_template_diseno_pendiente_validar')
            if template:
                template.with_context(
                    lang=self.env.user.lang,
                    user_name=self.env.user.name,
                ).send_mail(record.id, force_send=True, email_values=None)
            
            record.message_post(body=_("Diseño subido. Los datos del diseño ahora son de solo lectura."))
        return True

    @api.constrains('image')
    def _check_image_present(self):
        for record in self:
            if not record.image:
                raise ValidationError("Debe subir la imagen del diseño.")
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', **kwargs):
        """Sobrescribir para hacer los campos de solo lectura después de subir el diseño."""
        res = super(Design, self).fields_view_get(view_id=view_id, view_type=view_type, **kwargs)
        
        if view_type == 'form':
            doc = self.env['ir.ui.view'].browse(view_id)
            if doc and doc.model == 'design.design':
                for record in self:
                    if record.diseño_subido:
                        # Hacer que los campos no editables sean de solo lectura
                        for field in record._fields:
                            if field not in self._fields_editables_after_upload:
                                res['fields'].get(field, {})['readonly'] = True
        return res

