from mwi.core import *
from mwi.model import *
from mwi.export import Export
from os import walk

md = """**INCROYABLE.** En septembre 2015, en plein vol au-dessus de l'océan Atlantique (dans un long-courrier reliant l'Espagne à New York), un [bébé](https://www.sciencesetavenir.fr/tag_theme/bebe_6106/) de deux ans fait soudainement une crise d'[asthme](https://www.sciencesetavenir.fr/tag_maladie/asthme_8139/). Khurshid Guru, directeur du département de chirurgie robotisée au Roswell Park Cancer Institute de New York (États-Unis), alerté par les cris et le souffle coupé du bébé asthmatique, incite les parents à utiliser les pompes et les médicaments en urgence. Problème : ces derniers les ont oubliés dans leurs bagages à soute. _"Nous étions en vol depuis trois ou quatre heures. L'enfant était enrhumé et à cause de l'altitude, son état s'est rapidement détérioré"_, raconte à [_ABC News_](https://abcnews.go.com/Health/doctor-channels-macgyver-asthmatic-toddler-aboard-transatlantic-flight/story?id=34013909) le spécialiste. Le taux d'oxygène du bébé de deux ans chute à vue d'œil (jusqu'à 87 %), nécessitant au médecin de réagir sans attendre.
#### Une bouteille d'eau, un gobelet en plastique et un masque à oxygène
Mais le seul inhalateur disponible dans l’avion n’est adapté qu'aux adultes. Le médecin décide alors de bricoler lui-même une chambre à air sur mesure avec une bouteille d'eau vide, un gobelet en plastique et un masque à oxygène. Un dispositif improvisé dont il postera la photo sur Twitter (voir tweet ci-dessous).
> Flying back from ERUS15 had to design a nebuliser for a 2 yr old asthmatic over the atlantic. Thank God kid did well! [pic.twitter.com/fQOJ2Ac0EA](http://t.co/fQOJ2Ac0EA)
> — Khurshid A. Guru (@KhurshidGuru) [18 Septembre 2015](https://twitter.com/KhurshidGuru/status/644857926469976064)
_"Quand j'ai approché la bouteille du visage de l'enfant, il l'a immédiatement repoussé, alors j'ai ajouté au bout un petit verre de plastique. J'ai demandé aux parents de le tenir près de son nez et sa bouche"_, précise le médecin. Trente minutes plus tard, la crise d'asthme de l'enfant cesse et son taux d'oxygène remonte à 95 %. _"Quand l'avion a atterri, je l'ai vu en train de jouer avec sa mère"_. À travers ce témoignage, Khurshid Guru souhaite sensibiliser les parents d'enfants asthmatiques sur la nécessité de garder en bagage à main les traitements contre l’asthme quand ils prennent l'avion."""

links = extract_md_links(md)
print(links)
