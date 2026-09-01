"""ondelete cascade sur les cles etrangeres vers articles

Revision ID: b483485d15db
Revises: a9c9a268f410
Create Date: 2026-08-25 02:15:59.347380

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b483485d15db'
down_revision = 'a9c9a268f410'
branch_labels = None
depends_on = None


# (table, colonne, comportement) — CASCADE pour les données qui n'ont pas de
# sens sans leur article (sources, commentaires éditoriaux/lecteurs,
# historique) ; SET NULL pour collected_articles, qui doit garder son
# historique de collecte même si l'article publié est ensuite supprimé.
_CIBLES = [
    ('article_revisions', 'article_id', 'CASCADE'),
    ('article_sources', 'article_id', 'CASCADE'),
    ('collected_articles', 'published_article_id', 'SET NULL'),
    ('comments', 'article_id', 'CASCADE'),
    ('editorial_comments', 'article_id', 'CASCADE'),
]


def _nom_contrainte_fk(table, column, table_referencee='articles'):
    """Découvre le vrai nom de la contrainte, plutôt que de supposer la
    convention de nommage par défaut d'un moteur donné (elle diffère entre
    SQLite et PostgreSQL, et aucune de ces contraintes n'a jamais reçu de
    nom explicite dans les migrations d'origine) — vérifié avant d'écrire
    cette fonction : dropper une contrainte non nommée avec `None` échoue
    en mode batch avec "Constraint must have a name"."""
    bind = op.get_bind()
    inspecteur = sa.inspect(bind)
    for fk in inspecteur.get_foreign_keys(table):
        if fk.get("referred_table") == table_referencee and column in fk.get("constrained_columns", []):
            return fk.get("name")
    return None


def upgrade():
    for table, column, ondelete in _CIBLES:
        nom = _nom_contrainte_fk(table, column)
        with op.batch_alter_table(table, schema=None) as batch_op:
            if nom:
                batch_op.drop_constraint(nom, type_="foreignkey")
            batch_op.create_foreign_key(
                f"fk_{table}_{column}_articles", "articles", [column], ["id"], ondelete=ondelete
            )


def downgrade():
    for table, column, _ in reversed(_CIBLES):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_constraint(f"fk_{table}_{column}_articles", type_="foreignkey")
            batch_op.create_foreign_key(
                f"fk_{table}_{column}_articles_sans_cascade", "articles", [column], ["id"]
            )
