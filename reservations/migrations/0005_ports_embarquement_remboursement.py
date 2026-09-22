# Ports en entité réelle + statut de traversée + expiration des attentes
# + embarquements (check-in) + remboursements.
# La structure existante des lignes (port_depart / port_arrivee en texte libre)
# est migrée en douceur : les noms de ports deviennent des enregistrements Port,
# puis les colonnes texte sont remplacées par des clés étrangères.

import django.db.models.deletion
from django.db import migrations, models


def creer_ports_depuis_lignes(apps, schema_editor):
    """Transforme les noms de ports des lignes en enregistrements Port et relie."""
    Port = apps.get_model('reservations', 'Port')
    Route = apps.get_model('reservations', 'Route')
    routes = list(Route.objects.all())

    noms = set()
    for r in routes:
        noms.add(r.port_depart_texte)
        noms.add(r.port_arrivee_texte)

    ports_par_nom = {}
    for nom in sorted(n for n in noms if n):
        port, _ = Port.objects.get_or_create(nom=nom, defaults={'est_actif': True})
        ports_par_nom[nom] = port

    for r in routes:
        r.port_depart = ports_par_nom.get(r.port_depart_texte)
        r.port_arrivee = ports_par_nom.get(r.port_arrivee_texte)
        r.save(update_fields=['port_depart', 'port_arrivee'])


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0004_passager_reservation_rappel_envoye_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Port',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=80, unique=True, verbose_name='Nom du port')),
                ('ville', models.CharField(blank=True, max_length=80, verbose_name='Ville')),
                ('coordonnees_gps', models.CharField(blank=True, max_length=80, verbose_name='Coordonnées GPS', help_text='Ex: -2.50, 28.86')),
                ('telephone', models.CharField(blank=True, max_length=30, verbose_name='Téléphone')),
                ('est_actif', models.BooleanField(default=True, verbose_name='Actif')),
            ],
            options={
                'verbose_name': 'Port',
                'verbose_name_plural': 'Ports',
                'ordering': ['nom'],
            },
        ),
        # La contrainte d'unicité est retirée le temps de la refonte, puis recréée.
        migrations.RemoveConstraint(
            model_name='route',
            name='ligne_unique_depart_arrivee',
        ),
        migrations.RenameField(
            model_name='route',
            old_name='port_depart',
            new_name='port_depart_texte',
        ),
        migrations.RenameField(
            model_name='route',
            old_name='port_arrivee',
            new_name='port_arrivee_texte',
        ),
        migrations.AddField(
            model_name='route',
            name='port_depart',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='routes_depart', to='reservations.port', verbose_name='Port de départ'),
        ),
        migrations.AddField(
            model_name='route',
            name='port_arrivee',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='routes_arrivee', to='reservations.port', verbose_name="Port d'arrivée"),
        ),
        migrations.RunPython(creer_ports_depuis_lignes, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='route',
            name='port_depart_texte',
        ),
        migrations.RemoveField(
            model_name='route',
            name='port_arrivee_texte',
        ),
        migrations.AlterField(
            model_name='route',
            name='port_depart',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='routes_depart', to='reservations.port', verbose_name='Port de départ'),
        ),
        migrations.AlterField(
            model_name='route',
            name='port_arrivee',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='routes_arrivee', to='reservations.port', verbose_name="Port d'arrivée"),
        ),
        migrations.AddConstraint(
            model_name='route',
            constraint=models.UniqueConstraint(fields=('port_depart', 'port_arrivee'), name='ligne_unique_depart_arrivee'),
        ),
        migrations.AlterModelOptions(
            name='route',
            options={'ordering': ['port_depart__nom', 'port_arrivee__nom'], 'verbose_name': 'Ligne', 'verbose_name_plural': 'Lignes'},
        ),
        migrations.AddField(
            model_name='traversee',
            name='statut',
            field=models.CharField(choices=[('PROGRAMMEE', 'Programmée'), ('RETARDEE', 'Retardée'), ('PARTIE', 'Partie'), ('ANNULEE', 'Annulée')], default='PROGRAMMEE', max_length=12, verbose_name='Statut'),
        ),
        migrations.AddField(
            model_name='reservation',
            name='expire_le',
            field=models.DateTimeField(blank=True, editable=False, null=True, verbose_name='Paiement à effectuer avant'),
        ),
        migrations.CreateModel(
            name='Embarquement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_embarquement', models.DateTimeField(auto_now_add=True, verbose_name='Embarqué le')),
                ('reservation', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='embarquement', to='reservations.reservation', verbose_name='Réservation')),
                ('traversee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='embarquements', to='reservations.traversee', verbose_name='Traversée')),
                ('valide_par', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.user', verbose_name='Validé par')),
            ],
            options={
                'verbose_name': 'Embarquement',
                'verbose_name_plural': 'Embarquements',
                'ordering': ['-date_embarquement'],
            },
        ),
        migrations.CreateModel(
            name='Remboursement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('montant', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Montant remboursé (FC)')),
                ('motif', models.CharField(choices=[('ANNULATION', 'Annulation du billet'), ('TRAVERSEE_ANNULEE', 'Traversée annulée'), ('AUTRE', 'Autre motif')], default='ANNULATION', max_length=25, verbose_name='Motif')),
                ('notes', models.TextField(blank=True, verbose_name='Notes')),
                ('date_creation', models.DateTimeField(auto_now_add=True, verbose_name='Créé le')),
                ('cree_par', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.user', verbose_name='Créé par')),
                ('reservation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='remboursements', to='reservations.reservation', verbose_name='Réservation')),
            ],
            options={
                'verbose_name': 'Remboursement',
                'verbose_name_plural': 'Remboursements',
                'ordering': ['-date_creation'],
            },
        ),
    ]