# V2C Trydan pour Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Stable release](https://img.shields.io/github/v/release/Carbanog/V2C_trydan.svg)](https://github.com/Carbanog/V2C_trydan/releases/)
[English](README.md) · [Español](README.es.md) · [Français](README.fr.md)

Commande locale de la borne, suivi complet des sessions et outils facultatifs
pour gérer la recharge depuis Home Assistant.

V2C Trydan réunit commandes quotidiennes, sessions conservées entre les pauses
et redémarrages, diagnostics et exemples d’automatisations. La branche bêta ajoute
une programmation hebdomadaire par tarifs, indépendante du fournisseur d’énergie.

## Versions et périmètre

| Canal | Version | Usage |
| --- | --- | --- |
| Stable | [1.3.3](https://github.com/Carbanog/V2C_trydan/releases/tag/v1.3.3) | Suivi, commandes et sessions. |
| Bêta volontaire | [1.4.0b3](https://github.com/Carbanog/V2C_trydan/releases/tag/v1.4.0b3) | Programmation facultative ; installation de test uniquement. |

La bêta ne remplace pas la dernière version stable. Les fonctions marquées bêta
ci-dessous sont expérimentales, pas disponibles dans 1.3.3. Voir le [journal des
modifications](CHANGELOG.md), en anglais. Ce projet s’installe dans HACS comme
**dépôt personnalisé**, sans prétendre figurer dans son catalogue par défaut.

## Fonctions principales

- HTTP local : aucun compte V2C Cloud ni Octopus/OCPP requis.
- Pause, verrouillage et intensité, avec réglages avancés facultatifs.
- Énergie et temps actif de toute la session malgré les remises à zéro des
  compteurs partiels pendant les pauses.
- Restauration de la session après redémarrage de HA.
- Requêtes partagées et sérialisées, tentatives limitées et diagnostic de
  communication, également utiles sur les liaisons CPL/Wi-Fi limitées.
- Nouvelle adresse IP sans recréer l’intégration ; données sensibles connues masquées.
- Blueprints, tableaux de bord et interface en français, espagnol et anglais.

La tolérance aux pannes ne supprime pas les problèmes réseau et ne garantit pas la connexion.

## Prérequis et compatibilité

HA doit pouvoir joindre l’API HTTP locale de Trydan. Réservez son adresse dans
le routeur et vérifiez `http://IP_DE_LA_BORNE/RealTimeData` sur le même réseau.
N’exposez pas cette API sur Internet.

Les tests couvrent des réponses réelles anonymisées des firmwares 2.4.6 et 2.5.1 ;
ce n’est pas une validation physique de toutes les versions ou installations.
Les champs facultatifs sont détectés selon leur présence. Le firmware 2.5.2 et
les montages Trydan Pro maître/secondaire restent non validés.

Les mesures réelles de courant/tension L1 apparaissent si la borne les fournit.
Les phases L2/L3 et les commandes d’éclairage ne sont pas exposées ; l’éclairage
a été retiré à cause d’états locaux incohérents. L’affichage de l’icône locale
utilise l’API de marques disponible depuis HA 2026.3.

## Installation

[![Ajouter à HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Carbanog&repository=V2C_trydan&category=integration)

1. Sauvegardez HA.
2. Utilisez le bouton ou ajoutez `https://github.com/Carbanog/V2C_trydan` comme
   dépôt personnalisé de type **Intégration** dans HACS.
3. Téléchargez la stable **1.3.3**, puis redémarrez HA.
4. Ouvrez **Paramètres → Appareils et services → Ajouter une intégration → V2C Trydan**.
5. Saisissez l’adresse IP locale de la borne.

Sans HACS : téléchargez une release et copiez uniquement
`custom_components/v2c_trydan` vers `/config/custom_components/v2c_trydan`.
Redémarrez, puis reprenez à l’étape 4. N’installez pas simultanément deux
implémentations du domaine `v2c_trydan`. Évitez les contrôleurs concurrents
envoyant des commandes contradictoires.

## Mises à jour, bêta et retour arrière

Mettez à jour via HACS et redémarrez. Ne supprimez pas l’intégration : les
identifiants, personnalisations et sessions stockées sont conservés.
Utilisez **Reconfigurer** si l’IP change. Rechargez après une mise à jour du
firmware pour découvrir les nouveaux champs facultatifs.

Pour essayer **1.4.0b3**, choisissez-la explicitement dans la sélection de version
de HACS, en affichant les préversions si nécessaire, uniquement sur le HA de test.
N’activez pas les bêtas en production et ne laissez pas deux instances commander
la même borne.

Pour revenir à la stable, vérifiez la pause réelle, désactivez la programmation
si elle était utilisée, téléchargez **1.3.3** et redémarrez. Désactiver/décharger
ne reprend jamais automatiquement la charge. Les entités propres à la bêta
peuvent rester indisponibles ; les entrées utilisateur ne sont pas supprimées.

## Entités et configuration

| Groupe | Contenu |
| --- | --- |
| Commandes quotidiennes | Pause, verrouillage et intensité manuelle. |
| Session | Énergie, temps actif et bouton facultatif de réinitialisation. |
| Suivi | Puissance/énergie partielle, état de charge, puissance maison, câble et charge active. |
| Réglages facultatifs | Limites d’intensité, charge/mode dynamique, programmateur et pause dynamique. |
| Diagnostics/mesures facultatifs | Compteur, firmware, réseau, Wi-Fi, états internes et mesures L1. |
| Programmation bêta | Mode, tarif et état ; seulement après activation. |

Les nouvelles installations désactivent initialement les réglages avancés, les
données photovoltaïques/batterie et de nombreux diagnostics. Les choix existants
sont conservés. Activez les entités nécessaires dans **Paramètres → Appareils et
services → Entités**, en incluant les entités désactivées dans le filtre.
Activer une entité ne modifie pas la borne avant d’utiliser sa commande.

Choisissez la langue dans votre profil HA. Les identifiants existants, noms
personnalisés et textes saisis dans les tableaux ne sont pas renommés automatiquement.

## Comptabilisation des sessions

**Énergie de charge** est le compteur partiel du firmware. **Énergie de la session**
et **Temps de charge actif de la session** cumulent les incréments entre les pauses
et remises à zéro. Ils fonctionnent aussi sans Octopus, en charge manuelle.

Les totaux restent accessibles après débranchement ; la prochaine connexion
observée démarre une nouvelle session. Un défaut de la borne ne démarre pas une
nouvelle session lors du rétablissement. L’état est enregistré indépendamment
de Recorder. Le bouton facultatif de réinitialisation sert aux corrections exceptionnelles.

L’affichage utilise deux décimales ; le temps est stocké en secondes. Si une
ancienne entité affiche encore les secondes, choisissez les heures dans ses
réglages sans réinitialiser le total. L’énergie effacée par la borne pendant
l’arrêt de HA ne peut pas être reconstruite.

## Programmation par tarifs — bêta 1.4 uniquement

Module séparé, facultatif et **désactivé par défaut**, sans assistants ni
automatisations à créer. Plusieurs plages par jour, différents jours, tarifs
Pointe/Intermédiaire/Heures creuses et passage à minuit sont possibles.
Aucun horaire contractuel, jour férié ou prix n’est supposé ou téléchargé.

Dans **Configurer**, ajoutez ou modifiez les plages, choisissez les tarifs et activez le module.
**Enregistrer et appliquer** présente activation, plages et créneaux non définis,
puis exige une confirmation. Les chevauchements sont refusés ; hors plage,
la charge n’est pas autorisée.

| Mode | Comportement |
| --- | --- |
| Automatique | Autorise la charge uniquement pendant les tarifs sélectionnés. |
| Charger maintenant | Ignore les tarifs jusqu’à une connexion observée suivie d’un débranchement. |
| Pause | Maintient l’arrêt jusqu’au choix d’un autre mode. |

La première activation commence en Pause. Le module écrit seulement `Paused` :
il ne déverrouille pas et ne change ni l’intensité ni la régulation dynamique.
Quand il est activé, l’interrupteur habituel de pause sélectionne Pause à
l’activation et Charger maintenant à la désactivation.
L’état explique l’attente, affiche la prochaine plage comme attribut et crée un
avertissement dans **Réparations** si une commande reste non confirmée une minute.

**HA doit rester allumé et connecté.** Une panne peut empêcher l’arrêt à l’heure
prévue ; un débranchement/rebranchement entièrement hors connexion peut passer
inaperçu. La prochaine plage n’est pas une garantie de démarrage.
Ne combinez pas cette politique avec OCPP/Octopus ou d’autres horaires de charge.
Gardez la régulation dynamique et les protections électriques actives.

[Guide détaillé de la bêta en anglais](https://github.com/Carbanog/V2C_trydan/blob/v1.4.0b3/docs/scheduling.md).
Le passage en stable attend encore les essais physiques de recharge.

## Blueprints et automatisations

Les imports facultatifs sont dans [blueprints/automation](blueprints/automation).
Ils ne sont jamais installés ou activés automatiquement.

**Résumé et notifications de session**

[![Importer dans Home Assistant](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FCarbanog%2FV2C_trydan%2Fblob%2Fv1.4.0b3%2Fblueprints%2Fautomation%2Fsession_summary.yaml)

[Voir le YAML](blueprints/automation/session_summary.yaml). Actions au démarrage et
après débranchement, sans répéter chaque pause OCPP. Les actions de fin disposent
de `session_kwh`, `session_seconds`, `session_hours`, `session_duration`,
`estimated_percent`, `estimated_cost` et `estimated_range_km`.

Exemple de fin de session ; remplacez le service de notification :
```yaml
action: notify.mobile_app_votre_telephone
data:
  title: Recharge terminée
  message: "{{ session_kwh }} kWh · {{ session_duration }}"
```

**Alerte de puissance élevée**

[![Importer dans Home Assistant](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FCarbanog%2FV2C_trydan%2Fblob%2Fv1.4.0b3%2Fblueprints%2Fautomation%2Fhigh_power_alert.yaml)

[Voir le YAML](blueprints/automation/high_power_alert.yaml). Déclenche les actions
après dépassement d’un seuil pendant la durée choisie ; fournit `measured_power`.

Capacité, rendement, prix et consommation du véhicule sont des paramètres
facultatifs du blueprint. Pourcentage ajouté, coût et autonomie sont des estimations
de notification, pas le SOC fourni par le véhicule ni de nouveaux capteurs.

## Tableaux de bord

- [Natif, exemple en anglais](dashboards/native.en.yaml) : cartes standard de HA.
- [Mushroom, exemple en anglais](dashboards/mushroom.en.yaml) : nécessite Mushroom et Mini Graph Card.

Copiez le YAML dans une carte manuelle et adaptez les identifiants à votre
installation. Les exemples ne modifient jamais automatiquement vos tableaux.

| Tableau natif | Tableau Mushroom |
| :---: | :---: |
| [![Tableau natif](docs/images/dashboard-native.png)](docs/images/dashboard-native.png) | [![Tableau Mushroom](docs/images/dashboard-mushroom.png)](docs/images/dashboard-mushroom.png) |

Les captures montrent l’interface espagnole ; les entités suivent la langue de HA.

## Actions de compatibilité

Pour de nouvelles automatisations, utilisez les entités `switch`, `number` et
`select`. Les actions de compatibilité restent disponibles :
`v2c_trydan.set_intensity`, `v2c_trydan.set_min_intensity`,
`v2c_trydan.set_max_intensity` et `v2c_trydan.set_dynamic_power_mode`.
Précisez `config_entry_id` pour choisir entre plusieurs bornes.

Elles ne remplacent pas tous les réglages V2C. Ne changez pas les limites, la
charge dynamique ou les modes avancés protégeant votre installation sans les comprendre.

## Diagnostic et limites

Lecture partagée toutes les **15 s**, délai de **20 s**, jusqu’à **3 tentatives**
pour les erreurs transitoires, espacées de **2 s**. Requêtes sérialisées par borne.
Les erreurs HTTP permanentes, redirections et réponses incorrectes restent visibles.
Les commandes exigent `OK` et ne sont pas répétées à l’aveugle.

Pour signaler un problème, activez le journal de débogage de l’intégration, attendez
la panne et le rétablissement, puis désactivez-le et téléchargez les journaux/diagnostics.
Ils donnent tentatives, durée, dernier échec et rétablissement observé.
Le rétablissement automatique ne prouve pas une cause réseau.
IP, SSID et identifiant connus sont masqués dans les diagnostics ; vérifiez tout
journal ou capture avant publication.

Pas de SOC réel du véhicule, objectif en kilomètres, PVPC ni optimisation
automatique des prix. La programmation bêta n’est pas une protection de sécurité
ou une garantie tarifaire pendant les pannes de HA ou du réseau.

## Contribuer et préparer HACS

Utilisez les [Issues](https://github.com/Carbanog/V2C_trydan/issues) avec versions
de l’intégration, HA et firmware, étapes de reproduction et diagnostics vérifiés.
Les langues maintenues sont le français, l’espagnol et l’anglais ; les corrections
de locuteurs natifs sont bienvenues. D’autres langues pourront être ajoutées
selon la demande et les possibilités de maintenance.

[Architecture et développement](docs/architecture.md) ·
[Préparation du catalogue HACS](docs/hacs-readiness.md) — documents en anglais.

Les contrôles incluent Ruff, pytest, hassfest et HACS. La branche bêta teste aussi
le cycle HA réel avec une borne simulée ; cela ne remplace pas les essais physiques.
L’inclusion dans le catalogue HACS nécessite une demande et une revue séparées.

## Licence et crédits

Projet indépendant maintenu par [Carbanog](https://github.com/Carbanog), sans
affiliation à V2C ou Home Assistant. Le travail de
[Rain1971](https://github.com/Rain1971/V2C_trydant) est son point de départ ; le projet
a évolué avec ses propres fonctions et son architecture, en conservant cette reconnaissance.

[Licence MIT](LICENSE), avec les mentions des auteurs d’origine et de Carbanog
préservées. Merci à la communauté et aux outils d’IA utilisés pour développer et
relire le projet. L’origine de l’icône est documentée dans
[brand-assets](docs/brand-assets.md).
Soutien facultatif via **Sponsor this project**, dans la barre latérale du dépôt.
