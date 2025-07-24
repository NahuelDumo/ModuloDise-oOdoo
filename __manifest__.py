# modulo_diseno/__manifest__.py
{
    "name": "Modulo de Diseño",
    "version": "1.0",
    "category": "Project",
    "summary": "Gestión de listas de verificación para diseños con validación y etapas",
    "author": "Nahuel Dumo",
    "license": "AGPL-3",
    "depends": ["base", "project", "mail", "portal"],
    "data": [
        # Primero los archivos de seguridad
        "security/security.xml",
        "security/ir.model.access.csv",
        
        # Luego las vistas que definen las acciones
        "views/checklist_template_views.xml",
        "views/design_views.xml",
        "views/checklist_item_views.xml",
        "views/revision_log_views.xml",
        "views/wizard_views.xml",
        
        # Finalmente los menús que referencian las acciones
        "views/menu.xml"
    ],
    "application": True,
    "installable": True,
    "auto_install": False
}
