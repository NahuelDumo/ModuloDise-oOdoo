from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class Design(models.Model):
    _name = "design.design"
    _description = "Diseño"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = "create_date desc"
    
    def unlink(self):
        """Sobrescribir para controlar la eliminación de diseños"""
        for record in self:
            if not self.env.user.has_group('base.group_system'):
                raise AccessError(_("Solo los administradores pueden eliminar diseños."))
            
            # Registrar en el historial
            self.env['design.revision_log'].create({
                'design_id': record.id,
                'usuario_id': self.env.user.id,
                'observaciones': "Diseño eliminado",
                'tipo': 'rechazo',
            })
            
        return super(Design, self).unlink()
        
    def action_delete_designs(self):
        """Acción para eliminar múltiples diseños desde la vista de lista"""
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_("Solo los administradores pueden eliminar diseños."))
            
        # Verificar si hay algún registro seleccionado
        if not self:
            raise UserError(_("No hay registros seleccionados para eliminar."))
            
        # Confirmar antes de eliminar
        return {
            'name': _('Confirmar eliminación'),
            'type': 'ir.actions.act_window',
            'res_model': 'design.delete.confirm',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_design_ids': self.ids, 'default_count': len(self)},
        }
    
    # Campo calculado para verificar si la etapa 1 está completa
    etapa1_completa = fields.Boolean(
        'Etapa 1 Completa',
        compute='_compute_etapa1_completa',
        store=True
    )

    @api.depends('checklist_ids.validado_por_disenador', 'checklist_ids.etapa')
    def _compute_etapa1_completa(self):
        for record in self:
            items_etapa1 = record.checklist_ids.filtered(lambda x: x.etapa == 'etapa1')
            if not items_etapa1:
                record.etapa1_completa = False
            else:
                record.etapa1_completa = all(item.validado_por_disenador for item in items_etapa1)

    # Lista de campos que se pueden editar después de subir el diseño
    _fields_editables_after_upload = [
        'checklist_ids', 'comentario_validador', 'comentario_disenador',
        'visible_para_cliente', 'aprobado_cliente', 'rechazado', 'observaciones_rechazo',
        'contador_modificaciones', 'ultimo_mensaje_cliente', 'state',
        'fecha_aprobacion_cliente', 'fecha_rechazo', 'etapa1_completa'
    ]

    name = fields.Char("Nombre del diseño", required=True, tracking=True)
    attachment_ids = fields.One2many('design.image', 'design_id', string='Adjuntos del diseño')
    cliente_id = fields.Many2one("res.partner", string="Cliente", required=True, tracking=True)
    task_id = fields.Many2one("project.task", string="Tarea asociada", tracking=True)

    categoria_id = fields.Many2one("product.category", string="Categoría de producto", required=True)

    etapa = fields.Selection([
        ('etapa1', 'Etapa 1'),
        ('etapa2', 'Etapa 2'),
        ('completo', 'Completado')
    ], string="Etapa actual", default='etapa1', tracking=True)

    checklist_ids = fields.One2many("design.checklist_item", "design_id", string="Checklist")

    visible_para_cliente = fields.Boolean("Visible al cliente", default=True, tracking=True)
    aprobado_cliente = fields.Boolean("Aprobado por el cliente", default=False, tracking=True)

    rechazado = fields.Boolean("Rechazado", default=False, tracking=True)
    observaciones_rechazo = fields.Text("Observaciones de rechazo")

    historial_ids = fields.One2many("design.revision_log", "design_id", string="Historial de validaciones")

    fecha_aprobacion_cliente = fields.Datetime("Fecha de aprobación del cliente", readonly=True)
    fecha_rechazo = fields.Datetime("Fecha de rechazo", readonly=True)
    fecha_estado_cliente = fields.Datetime("Fecha cuando pasó a estado cliente", readonly=True)

    state = fields.Selection([
        ('borrador', 'Borrador'),
        ('validacion', 'Esperando validación'),
        ('cliente', 'Esperando cliente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('correcciones_solicitadas', 'Correcciones Solicitadas'),
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
                                      
    # Campos para control de modificaciones del cliente
    contador_modificaciones = fields.Integer("Modificaciones solicitadas", default=0, 
                                           help="Número de veces que el cliente ha solicitado modificaciones")
    ultimo_mensaje_cliente = fields.Text("Último mensaje del cliente", 
                                       help="Último mensaje del cliente solicitando correcciones")
                                      
    # Campos calculados para permisos
    is_designer = fields.Boolean(compute='_compute_user_roles', string='Is Designer')
    is_validator = fields.Boolean(compute='_compute_user_roles', string='Is Validator')

    access_url = fields.Char(
        'Portal URL', compute='_compute_access_url',
        help='URL para que el usuario pueda acceder a este objeto a través del portal.')

    def _compute_access_url(self):
        for record in self:
            record.access_url = f'/my/design/{record.id}'
    
    def _compute_user_roles(self):
        for record in self:
            record.is_designer = self.env.user.has_group('ModuloDisenoOdoo.group_disenador')
            record.is_validator = self.env.user.has_group('ModuloDisenoOdoo.group_validador')

    is_designer = fields.Boolean(compute='_compute_user_roles', string='Is Designer')
    is_validator = fields.Boolean(compute='_compute_user_roles', string='Is Validator')

    def _compute_user_roles(self):
        for record in self:
            record.is_designer = self.env.user.has_group('ModuloDisenoOdoo.group_disenador')
            record.is_validator = self.env.user.has_group('ModuloDisenoOdoo.group_validador')

    def _cargar_checklist_etapa(self):
        """
        Carga automáticamente los items de checklist para la etapa actual del diseño.
        Solo carga la plantilla si existe para la etapa actual.
        
        Returns:
            bool: True si se cargó la plantilla, False si no se encontró
        """
        self.ensure_one()
        
        # Buscar plantilla para la categoría y etapa actual
        template = self.env['design.checklist_template'].search([
            ('categoria_id', '=', self.categoria_id.id),
            ('etapa', '=', self.etapa)
        ], limit=1)
        
        if not template:
            _logger.info(f"No se encontró plantilla de checklist para la categoría {self.categoria_id.name} y etapa {self.etapa}")
            return False
            
        try:
            # Eliminar items de checklist existentes para esta etapa
            self.checklist_ids.filtered(lambda x: x.etapa == self.etapa).unlink()
            
            # Crear nuevos items basados en la plantilla
            for item_template in template.item_ids:
                self.env['design.checklist_item'].create({
                    'name': item_template.name,
                    'design_id': self.id,
                    'etapa': self.etapa,
                    'orden': item_template.orden,
                })
                
            _logger.info(f"Se cargó la plantilla de checklist para la etapa {self.etapa}")
            return True
            
        except Exception as e:
            _logger.error(f"Error al cargar la plantilla de checklist: {str(e)}")
            self.message_post(body=f"Error al cargar la plantilla de checklist: {str(e)}", message_type="comment", subtype="mt_comment")
            return False

    def _transicion_a_etapa2_aprobado(self):
        """
        Maneja la transición a etapa 2 cuando el diseño es aprobado por el cliente.
        Si existe plantilla de etapa 2: elimina items de etapa 1 y carga los de etapa 2.
        Si NO existe plantilla de etapa 2: mantiene los items de etapa 1.
        """
        self.ensure_one()
        
        # Buscar plantilla de etapa 2 primero
        template = self.env['design.checklist_template'].search([
            ('categoria_id', '=', self.categoria_id.id),
            ('etapa', '=', 'etapa2')
        ], limit=1)
        
        if template:
            # Si existe plantilla de etapa 2: eliminar items de etapa 1 y cargar etapa 2
            items_etapa1 = self.checklist_ids.filtered(lambda x: x.etapa == 'etapa1')
            if items_etapa1:
                items_etapa1.unlink()
                _logger.info(f"Eliminados {len(items_etapa1)} items de checklist de etapa 1")
            
            # Crear items de etapa 2
            for item_template in template.item_ids.sorted(lambda x: x.orden):
                self.env['design.checklist_item'].create({
                    'name': item_template.name,
                    'design_id': self.id,
                    'etapa': 'etapa2',
                    'orden': item_template.orden,
                    'comentario': item_template.comentario_default or '',
                })
            
            _logger.info(f"Cargados {len(template.item_ids)} items de checklist para etapa 2")
            self.message_post(body="Diseño aprobado por cliente. Se ha cargado el checklist de Etapa 2.")
        else:
            # Si NO existe plantilla de etapa 2: mantener items de etapa 1
            _logger.info(f"No se encontró plantilla de etapa 2 para categoría {self.categoria_id.name}. Manteniendo items de etapa 1.")
            self.message_post(body="Diseño aprobado por cliente. Se mantiene el checklist de Etapa 1 (no hay plantilla para Etapa 2).")
        
        # Cambiar a etapa 2 en ambos casos
        self.etapa = 'etapa2'
        return True

    @api.depends('checklist_ids.validado_por_disenador', 'checklist_ids.validado_por_validador')
    def _compute_estado_checklist(self):
        for record in self:
            checklist = record.checklist_ids.filtered(lambda x: x.etapa == record.etapa)
            completo_disenador = checklist and all(item.validado_por_disenador for item in checklist)
            completo_validador = checklist and all(item.validado_por_validador for item in checklist)

            if completo_disenador and record.state == 'borrador':
                record.state = 'validacion'

            if completo_validador and record.state == 'validacion':
                record.state = 'cliente'
                # NO cambiar etapa ni cargar checklist aquí
                # La transición a etapa2 solo debe ocurrir cuando el cliente aprueba
                record.message_post(body="Checklist validado por el validador. Diseño enviado al cliente para aprobación.")
                record._notificar_a_disenador()

    def _notificar_a_validadores(self):
        validadores = self.env.ref('ModuloDisenoOdoo.group_validador').users
        template = self.env.ref('ModuloDisenoOdoo.email_template_diseno_pendiente_validar')
        for validador in validadores:
            template.send_mail(self.id, force_send=True, email_values={'email_to': validador.email})

    def _notificar_a_disenador(self):
        # Cambiado de 'email_template_diseño_validado' a 'email_template_diseno_validado' (sin la ñ)
        template = self.env.ref('ModuloDisenoOdoo.email_template_diseno_validado')
        template.send_mail(self.id, force_send=True, email_values={'email_to': self.create_uid.email})

    def action_rechazar_diseno(self):
        """Abre un wizard para que el validador ingrese los motivos del rechazo."""
        self.ensure_one()
        
        # Verificar permisos
        if not self.env.user.has_group('ModuloDisenoOdoo.group_validador') and not self.env.user.has_group('base.group_system'):
            raise AccessError(_("Solo los validadores pueden rechazar diseños."))
            
        # Verificar que el diseño esté en un estado que permita el rechazo
        if self.state not in ['validacion', 'cliente']:
            raise UserError(_("No se puede rechazar un diseño en el estado actual (solo en validación o cliente)."))
            
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
        """Marca el diseño como rechazado, limpia los campos y notifica."""
        self.ensure_one()

        # 1. Registrar en el historial antes de cambiar el estado
        self.env['design.revision_log'].create({
            'design_id': self.id,
            'tipo': 'rechazo',
            'observaciones': f'Diseño rechazado. Estado anterior: {self.state}. Motivo: {motivo}',
            'usuario_id': self.env.user.id,
        })

        # 2. Eliminar todos los adjuntos (ir.attachment)
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'design.design'),
            ('res_id', '=', self.id)
        ])
        if attachments:
            attachments.unlink()

        # 3. Resetear los checklist items
        for item in self.checklist_ids:
            item.write({
                'validado_por_disenador': False,
                'validado_por_validador': False,
                'fecha_disenador': None,
                'fecha_validador': None,
            })

        # 4. Limpiar campos, excepto los especificados
        vals_to_clear = {
            'etapa': 'etapa1',
            'state': 'rechazado',
            'rechazado': True,
            'observaciones_rechazo': motivo,
            'fecha_rechazo': fields.Datetime.now(),
            'comentario_validador': '',
            'comentario_disenador': '',
            'ultimo_mensaje_cliente': '',
            'aprobado_cliente': False,
            'fecha_aprobacion_cliente': None,
            'diseño_subido': False, # Permite volver a subir
            'fecha_subida_diseno': None,
        }
        self.write(vals_to_clear)

        # 5. Enviar notificación por correo al diseñador
        template = self.env.ref('ModuloDisenoOdoo.email_template_diseno_rechazado', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
            
            # Notificar al diseñador
            self.message_post(
                body=_(f"""
                <p>El diseño ha sido rechazado por el validador.</p>
                <p><strong>Motivo del rechazo:</strong> {motivo}</p>
                <p>Por favor, suba un nuevo diseño con las correcciones solicitadas.</p>
                """),
                subject=_("Diseño Rechazado - Se requiere nueva versión"),
                partner_ids=[self.create_uid.partner_id.id] if self.create_uid.partner_id else []
            )
            
            # Enviar notificación por correo
            template = self.env.ref('ModuloDisenoOdoo.email_template_diseno_rechazado', False)
            if template:
                template.with_context(
                    lang=self.env.user.lang,
                    user_name=self.env.user.name,
                    motivo_rechazo=motivo
                ).send_mail(self.id, force_send=True, email_values={
                    'email_to': self.create_uid.email if self.create_uid else False
                })
        return True


    @api.model
    def create(self, vals):
        # Asignar cliente desde la tarea si existe
        if 'task_id' in vals and vals.get('task_id'):
            task = self.env['project.task'].browse(vals['task_id'])
            if task.exists() and task.partner_id:
                if not vals.get('cliente_id'):
                    vals['cliente_id'] = task.partner_id.id

            
        # Crear el registro
        new_design = super(Design, self).create(vals)

        # Añadir al cliente como seguidor para el acceso al portal
        if new_design.cliente_id:
            new_design.message_subscribe(partner_ids=new_design.cliente_id.ids)
        
        # Registrar en el historial
        self.env['design.revision_log'].create({
            'design_id': new_design.id,
            'usuario_id': self.env.uid,
            'tipo': 'creacion',
            'observaciones': 'Diseño creado y listo para comenzar.'
        })
        
        # Enviar notificación al diseñador si corresponde
        if new_design.create_uid and new_design.create_uid.email:
            template = self.env.ref('modulo_diseno.email_template_diseno_creado', raise_if_not_found=False)
            if template:
                template.with_context(
                    lang=new_design.create_uid.lang,
                    user_name=new_design.create_uid.name,
                ).send_mail(new_design.id, force_send=True, email_values={
                    'email_to': new_design.create_uid.email
                })
        
        categoria_id = vals.get('categoria_id')
        if not categoria_id:
            return new_design

        plantilla = self.env['design.checklist_template'].search([
            ('categoria_id', '=', categoria_id),
            ('etapa', '=', 'etapa1')
        ], limit=1)

        if plantilla:
            for item in plantilla.item_ids.sorted(key=lambda x: x.orden):
                self.env['design.checklist_item'].create({
                    'name': item.name,
                    'design_id': new_design.id,
                    'comentario': item.comentario_default or '',
                })

        return new_design

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
        """
        Envía notificación al validador cuando el diseñador completa el checklist.
        Este método se llama desde el write cuando se detecta que se ha completado el checklist.
        """
        for record in self:
            if record._check_checklist_completo():
                # Registrar primero en el historial que el diseñador completó su checklist
                self.env['design.revision_log'].create({
                    'design_id': record.id,
                    'usuario_id': self.env.user.id,
                    'tipo': 'validacion_disenador',
                    'observaciones': 'El diseñador ha completado el checklist. Enviando notificación al validador.'
                })
                
                # Enviar notificación al validador
                template = self.env.ref('ModuloDisenoOdoo.modulolistasdeverificacion_email_template_checklist_completado', raise_if_not_found=False)
                if template:
                    template.with_context(
                        lang=self.env.user.lang,
                        user_name=self.env.user.name,
                    ).send_mail(record.id, force_send=True, email_values=None)
                    
                    # Registrar que se envió la notificación al validador
                    self.env['design.revision_log'].create({
                        'design_id': record.id,
                        'usuario_id': self.env.user.id,
                        'tipo': 'validacion_disenador',
                        'observaciones': 'Notificación enviada al validador para revisar el checklist completado.'
                    })

    def write(self, vals):
        # Verificar si se están modificando campos protegidos después de subir el diseño
        if any(record.diseño_subido for record in self):
            # Filtrar solo los campos editables
            protected_fields = set(vals.keys()) - set(self._fields_editables_after_upload)
            if protected_fields:
                # Verificar si el usuario es administrador o validador
                is_validador = self.env.user.has_group('ModuloDisenoOdoo.group_validador')
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
                # Registrar fecha cuando pasa a estado cliente
                if vals["state"] == 'cliente' and record.state != 'cliente':
                    vals['fecha_estado_cliente'] = fields.Datetime.now()
                    
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

    def abrir_wizard_rechazo(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'design.rechazo.wizard',  # Nombre corregido
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_design_id': self.id
            }
        }


    def get_validators_emails(self):
        group = self.env.ref('ModuloDisenoOdoo.group_validador')
        return ','.join(user.partner_id.email for user in group.users if user.partner_id.email)

    def get_disenador_email(self):
        # Busca el diseñador como quien validó al principio
        disenador = self.checklist_ids.filtered(lambda i: i.usuario_disenador)
        if disenador:
            return disenador[0].usuario_disenador.partner_id.email
        return self.env.user.partner_id.email  # fallback

    def subir_diseno(self):
        """Marca el diseño como subido y congela los datos."""
        self.ensure_one()
        
        # Verificar que se haya subido una imagen
        if not self.attachment_ids:
            raise UserError(_("Debe subir al menos un archivo adjunto antes de continuar."))
            
        # Limpiar observaciones de rechazo después de usarlas
        if self.observaciones_rechazo:
            self.observaciones_rechazo = False
            
        # Si es la primera vez que se sube el diseño
        elif self.state == 'borrador':
            self.state = 'validacion'
            self.env['design.revision_log'].create({
                'design_id': self.id,
                'tipo': 'subida',
                'observaciones': 'Primera versión del diseño subida.'
            })
        
        # Si se está reemplazando un diseño existente
        else:
            self.env['design.revision_log'].create({
                'design_id': self.id,
                'tipo': 'actualizacion',
                'observaciones': 'Diseño actualizado.'
            })
            
        # Notificar a los validadores si no es una actualización después de rechazo (ya se notificó arriba)
        if not self.rechazado and self.state == 'validacion':
            self.message_post(
                body=_("""
                <p>Se ha subido un nuevo diseño para validación.</p>
                <p>Por favor, revise el diseño y realice la validación correspondiente.</p>
                """),
                subject=_("Nuevo diseño para validar: %s") % self.name,
                partner_ids=[user.partner_id.id for user in self.env.ref('ModuloDisenoOdoo.group_validador').users]
            )
        
        return True

    @api.constrains('image_ids')
    def _check_image_present(self):
        for record in self:
            if not record.image_ids:
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

    def solicitar_nueva_verificacion(self):
        """Abre el wizard para subir una nueva versión del diseño."""
        self.ensure_one()
        
        # Verificar permisos
        if not self.env.user.has_group('ModuloDisenoOdoo.group_disenador') and not self.env.user.has_group('base.group_system'):
            raise AccessError(_("Solo los diseñadores pueden solicitar una nueva verificación."))
            
        if self.state != 'rechazado':
            raise UserError(_("Solo se puede solicitar una nueva verificación para diseños rechazados."))
        
        # Abrir el wizard para subir la nueva imagen
        return {
            'name': _('Subir Nueva Versión del Diseño'),
            'type': 'ir.actions.act_window',
            'res_model': 'design.subir.diseno.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_design_id': self.id,
            },
        }

    @api.constrains('attachment_ids')
    def _check_attachments(self):
        for record in self:
            if record.attachment_ids:
                image_count = 0
                for attachment in record.attachment_ids:
                    # Contar imágenes
                    if attachment.mimetype and attachment.mimetype.startswith('image'):
                        image_count += 1
                    
                    # Validar tamaño de PDF
                    if attachment.mimetype == 'application/pdf':
                        if attachment.file_size > 10 * 1024 * 1024: # 10 MB
                            raise ValidationError(_("El archivo PDF '%s' excede el límite de 10 MB.") % attachment.name)

                # Validar cantidad de imágenes
                if image_count > 20:
                    raise ValidationError(_("No se pueden subir más de 20 imágenes."))

    def action_aprobado_por_cliente(self):
        """Acción cuando el cliente aprueba el diseño"""
        self.ensure_one()
        self.state = 'aprobado'
        self.aprobado_cliente = True
        self.fecha_aprobacion_cliente = fields.Datetime.now()
        # Notificar a diseñador y validador
        self.notificar_aprobacion_cliente()
    
    def notificar_aprobacion_cliente(self):
        """Notificar aprobación del cliente"""
        template = self.env.ref('ModuloDisenoOdoo.email_template_diseno_aprobado_cliente', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
    
    def notificar_rechazo_cliente(self):
        """Notificar rechazo del cliente"""
        template = self.env.ref('ModuloDisenoOdoo.email_template_diseno_rechazado_cliente', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
    
    def notificar_correcciones_solicitadas(self):
        """Notificar que se solicitan correcciones"""
        template = self.env.ref('ModuloDisenoOdoo.email_template_correcciones_solicitadas', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
    def marcar_como_aprobado_por_cliente(self):
        """Marca el diseño como aprobado por el cliente"""
        self.ensure_one()
        
        # Realizar la transición a etapa 2 con checklist limpio
        self._transicion_a_etapa2_aprobado()
        
        self.write({
            'state': 'aprobado',
            'fecha_aprobacion_cliente': fields.Datetime.now(),
            'aprobado_cliente': True,
            'rechazado': False
        })
        
        # Registrar en el historial
        self.env['design.revision_log'].create({
            'design_id': self.id,
            'usuario_id': self.env.user.id,
            'tipo': 'aprobacion_cliente',
            'observaciones': 'Diseño aprobado por cliente. Transición a Etapa 2 con nuevo checklist.'
        })
        
        return True
        
        
    def action_solicitar_correcciones(self, mensaje_cliente):
        """Acción cuando el cliente aprueba con correcciones"""
        self.ensure_one()

        # Incrementar contador de modificaciones
        self.contador_modificaciones += 1
        self.ultimo_mensaje_cliente = mensaje_cliente
        self.state = 'correcciones_solicitadas'

        # Registrar en historial
        self.env['design.revision_log'].create({
            'design_id': self.id,
            'usuario_id': self.env.user.id,
            'tipo': 'correcciones_cliente',
            'observaciones': mensaje_cliente or 'Cliente solicitó correcciones'
        })

        # Notificar al diseñador/validador
        self.notificar_correcciones_solicitadas()
        return True

    def action_rechazado_por_cliente(self, motivo):
        """Acción cuando el cliente rechaza el diseño desde el portal"""
        self.ensure_one()

        self.rechazado = True
        self.state = 'rechazado'
        self.observaciones_rechazo = motivo
        self.fecha_rechazo = fields.Datetime.now()

        # Registrar en historial
        self.env['design.revision_log'].create({
            'design_id': self.id,
            'usuario_id': self.env.user.id,
            'tipo': 'rechazo_cliente',
            'observaciones': motivo or 'Cliente rechazó el diseño'
        })

        # Notificar al diseñador/validador
        self.notificar_rechazo_cliente()
        return True

