from wagtail import hooks


@hooks.register("register_log_actions")
def enregistrer_actions(actions):
    actions.register_action("kaloum24.import", "Import d'un article", "Article importé depuis un fichier")
