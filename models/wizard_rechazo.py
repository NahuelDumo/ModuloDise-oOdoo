from odoo import models, fields

class WizardRechazoDesign(models.TransientModel):
    _name = "design.wizard_rechazo"
    _description = "Motivo de rechazo del diseño"

    observacion = fields.Text("Observación", required=True)
    design_id = fields.Many2one("design.design", string="Diseño relacionado")

    def aplicar_rechazo(self):
        self.ensure_one()
        self.design_id.marcar_como_rechazado(self.observacion)
