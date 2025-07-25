from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime

class ChecklistItem(models.Model):
    _name = "design.checklist_item"
    _description = "Ítem de checklist aplicado a diseño"
    _order = "orden asc"

    name = fields.Char("Descripción", required=True)
    orden = fields.Integer("Orden", default=1)
    design_id = fields.Many2one("design.design", string="Diseño relacionado", ondelete="cascade")

    comentario = fields.Text("Comentario")

    # Validación diseñador
    validado_por_disenador = fields.Boolean("Validado por Diseñador")
    fecha_disenador = fields.Datetime("Fecha validación diseñador", readonly=True)
    usuario_disenador = fields.Many2one("res.users", string="Usuario diseñador", readonly=True)

    # Validación validador
    validado_por_validador = fields.Boolean("Validado por Validador")
    fecha_validador = fields.Datetime("Fecha validación validador", readonly=True)
    usuario_validador = fields.Many2one("res.users", string="Usuario validador", readonly=True)

    @api.onchange('validado_por_disenador')
    def _onchange_validado_disenador(self):
        if self.validado_por_disenador and not self.usuario_disenador:
            self.fecha_disenador = fields.Datetime.now()
            self.usuario_disenador = self.env.user

    @api.onchange('validado_por_validador')
    def _onchange_validado_validador(self):
        if self.validado_por_validador and not self.usuario_validador:
            self.fecha_validador = fields.Datetime.now()
            self.usuario_validador = self.env.user

    def write(self, vals):
        res = super().write(vals)

        for item in self:
            design = item.design_id

            if vals.get('validado_por_disenador') and not item.usuario_disenador:
                item.fecha_disenador = fields.Datetime.now()
                item.usuario_disenador = self.env.user
                self.env['design.revision_log'].create({
                    'design_id': design.id,
                    'usuario_id': self.env.user.id,
                    'observaciones': f"Ítem validado por diseñador: {item.name}",
                    'tipo': 'validacion_disenador',
                })

            if vals.get('validado_por_validador') and not item.usuario_validador:
                item.fecha_validador = fields.Datetime.now()
                item.usuario_validador = self.env.user
                self.env['design.revision_log'].create({
                    'design_id': design.id,
                    'usuario_id': self.env.user.id,
                    'observaciones': f"Ítem validado por validador: {item.name}",
                    'tipo': 'validacion_validador',
                })

        return res
