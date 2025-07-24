# modulo_diseno/models/checklist_template_item.py

from odoo import models, fields

class ChecklistTemplateItem(models.Model):
    _name = "design.checklist_template_item"
    _description = "Ítem de plantilla de checklist"

    name = fields.Char("Descripción del ítem", required=True)
    template_id = fields.Many2one("design.checklist_template", string="Plantilla", required=True, ondelete="cascade")
    orden = fields.Integer("Orden")

    comentario_default = fields.Text("Comentario por defecto (opcional)")
