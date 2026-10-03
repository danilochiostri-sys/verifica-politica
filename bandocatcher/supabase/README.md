# BandoCatcher — account ed email

La registrazione email non viene salvata in GitHub Pages, nel repository o in localStorage.

## Dove vive l'email

L'identità dell'utente è gestita da Supabase Auth, nella tabella protetta auth.users.

## Cosa vive nel database applicativo

public.profiles contiene soltanto i dati necessari al profilo e al matching.

public.alert_preferences contiene le preferenze degli alert.

public.saved_opportunities contiene i salvataggi personali.

## Sicurezza

Le tabelle applicative usano Row Level Security. Le policy consentono a un utente di leggere/modificare soltanto le proprie righe.

## Setup

1. Creare un progetto Supabase.
2. Eseguire schema.sql nel SQL Editor.
3. Inserire URL progetto e publishable/anon key in config.js.
4. Configurare email confirmation e URL di redirect nel pannello Supabase.
5. Non inserire mai una service_role key nel frontend.

La ricerca pubblica resta libera: l'account è necessario soltanto per funzioni personali come salvataggi e notifiche.
