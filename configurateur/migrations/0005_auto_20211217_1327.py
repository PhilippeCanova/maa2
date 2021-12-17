# Generated by Django 3.2.10 on 2021-12-17 13:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('configurateur', '0004_alter_region_tag'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='configmaa',
            options={'ordering': ['station', 'type_maa', 'seuil'], 'verbose_name': 'Configuration MAA', 'verbose_name_plural': 'Configurations MAA'},
        ),
        migrations.AlterModelOptions(
            name='station',
            options={'verbose_name': 'Aéroport'},
        ),
        migrations.AlterField(
            model_name='configmaa',
            name='type_maa',
            field=models.CharField(choices=[('BLSN', 'BLSN '), ('DENSE_FG', 'Brouillard dense'), ('DS', 'DS '), ('DU', 'DU '), ('FG', 'FG '), ('FWID', 'FWID '), ('FWOID', 'FWOID '), ('FZDZ', 'FZDZ'), ('FZFG', 'FZFG '), ('FZRA', 'FZRA '), ('GR', 'GR '), ('HVY_FZDZ', 'HVY_FZDZ '), ('HVY_FZRA', 'HVY_FZRA '), ('HVY_GR', 'HVY_GR '), ('HVY_SN', 'HVY_SN '), ('HVY_SNRA', 'HVY_SNRA '), ('HVY_SWELL', 'HVY_SWELL'), ('HVY_TS', 'HVY_TS '), ('ICE_DEPOSIT', 'ICE_DEPOSIT '), ('INV_TEMPE', 'INV_TEMPE'), ('RIME', 'RIME '), ('RR1', 'RR1 '), ('RR12', 'RR12 '), ('RR24', 'RR24 '), ('RR3', 'RR3 '), ('RR6', 'RR6 '), ('SA', 'SA '), ('SEA', 'SEA '), ('SN', 'SN'), ('SNRA', 'SNRA '), ('SQ', 'Grain'), ('SS', 'SS '), ('TC', 'TC '), ('TMAX', 'TMAX '), ('TMIN', 'TMIN '), ('TOXCHEM', 'TOXCHEM '), ('TS', 'Orage'), ('TSUNAMI', 'TSUNAMI '), ('VA', 'VA '), ('VEHICLE_RIME', 'VEHICLE_RIME '), ('VENT', 'VENT '), ('VENT_MOY', 'VENT_MOY')], max_length=20, verbose_name='Type MAA'),
        ),
    ]