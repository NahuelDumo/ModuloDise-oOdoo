from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime

class Design(models.Model):
    _name = "design.design"
    _description = "Diseño"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "create_date desc"

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

    def marcar_como_rechazado(self, observacion):
        self.rechazado = True
        self.observaciones_rechazo = observacion
        self.fecha_rechazo = fields.Datetime.now()
        self.visible_para_cliente = False
        self.aprobado_cliente = False
        self.etapa = 'etapa1'
        self.state = 'rechazado'

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

        self.env['design.revision_log'].create({
            'design_id': self.id,
            'usuario_id': self.env.user.id,
            'observaciones': 'Aprobado por cliente',
            'tipo': 'aprobacion_cliente',
        })

    @api.model
    def create(self, vals):
        record = super(Design, self).create(vals)

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

    def write(self, vals):
        result = super(Design, self).write(vals)

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

    @api.constrains('image')
    def _check_image_present(self):
        for record in self:
            if not record.image:
                raise ValidationError("Debe subir la imagen del diseño.")

