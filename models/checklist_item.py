# modulo_diseno/models/checklist_item.py

from odoo import models, fields
from odoo.exceptions import ValidationError
from datetime import datetime

class ChecklistItem(models.Model):
    _name = "design.checklist_item"
    _description = "Item de checklist aplicado a diseño"

    name = fields.Char("Descripción", required=True)
    design_id = fields.Many2one("design.design", string="Diseño relacionado", ondelete="cascade")

    validado_por_disenador = fields.Boolean("Validado por Diseñador")
    fecha_disenador = fields.Datetime("Fecha validación diseñador")
    usuario_disenador = fields.Many2one("res.users", string="Usuario diseñador")

    validado_por_validador = fields.Boolean("Validado por Validador")
    fecha_validador = fields.Datetime("Fecha validación validador")
    usuario_validador = fields.Many2one("res.users", string="Usuario validador")

    comentario = fields.Text("Comentario")

    @api.onchange('validado_por_disenador')
    def _onchange_validado_disenador(self):
        if self.validado_por_disenador:
            self.fecha_disenador = fields.Datetime.now()
            self.usuario_disenador = self.env.user

    @api.onchange('validado_por_validador')
    def _onchange_validado_validador(self):
        if self.validado_por_validador:
            self.fecha_validador = fields.Datetime.now()
            self.usuario_validador = self.env.user
