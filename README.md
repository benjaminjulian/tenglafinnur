# Tenglafinnur
Þessi vél leitar uppi brotna tengla og reynir að laga þá. Skimun eftir brotnum tenglum virkar á öllum síðum, en viðgerðarmaskínan er smíðuð fyrir WordPress.

## Notkun
Hægt er að velja þrjár æðar til að sækja gögn úr:

- Gagnasarpur WordPress síðunnar (Media mappan)
- Staðvær mappa
- Vefsafn.is

Til að leita í gagnasarpinum og uppfæra WordPress síður þarf að setja ENV (eða búa til .env skjal samhliða forritinu) með eftirfarandi stikum:

```
WP_USER=[WordPress notandinn]
WP_PASS=[WordPress forritunarlykill]
```

Forritunarlykillinn er búinn til í notandastillingunum, neðst á síðunni (./wp-admin/profile.php).

Skipunin til að keyra forritið er þessi:

```
python main.py [--skima] [--media] [--vefsafn] [--mappa MAPPA] vefur
```

- ```--skima``` stikinn leitar að brotnum tenglum.
- ```--media``` stikinn leitar að lagfæringum brotinna tengla í gagnasarpi WordPress.
- ```--vefsafn``` stikinn leitar að týndum skrám í Vefsafn.is.
- ```--mappa MAPPA``` stikinn skilgreinir staðværa möppu sem leitað er í að týndum skrám.

## Öryggisatriði
Athugið að **vélin parar skrár aðeins útfrá nafni** og því er mögulegt að rangar skrár séu tengdar ef þær heita nákvæmlega það sama. Aðeins er beðið um staðfestingu þegar nokkrar skrár í staðværu möppunni heita það sama og brotni tengillinn. Ekki hafa viðkvæm gögn í pörunarmöppunni eða WordPress gagnasarpinum nema að vel athuguðu máli.

## Fyrirvarar og smáatriði
- Þegar slegið er inn ```blabla.is/undirsida```, þá er aðeins leitað á ```/undirsida``` og ```/undirsida/*```, ekki á t.d. ```blabla.is```.
- Forritið býr til vinnumöppuna ```tmp``` og bæði skrifar og yfirskrifar í hana. Ekki geyma neitt þar!
- Hægt er að drepa á forritinu (Ctrl+C) hvenær sem er. Staða vinnslunnar er vistuð og hægt er að byrja aftur þar sem frá var horfið.