from enum import Enum
import aiohttp
import asyncio


class Link(Enum):
    CUTOFF_GM = "https://www.replays.lol/cutoff/EUW/grandmaster"
    CUTOFF_CH = "https://www.replays.lol/cutoff/EUW/challenger"

    # DA COMPLETARE: inserisci qui i tuoi altri 4 link che si aggiornano ogni 5 minuti (300s)
    LINK_300_1 = "https://www.replays.lol/cutoff/EUW/master"
    LINK_300_2 = "https://www.replays.lol/cutoff/EUW/diamond"
    LINK_300_3 = "https://www.replays.lol/cutoff/EUW/emerald"
    LINK_300_4 = "https://www.replays.lol/cutoff/EUW/platinum"

    def format(self, *args, **kwargs):
        return self.value.format(*args, **kwargs)


# Dizionario globale in cui puoi salvare i risultati per poi leggerli dal Bot
scraped_data = {}


async def fetch_cutoff(session: aiohttp.ClientSession, url: str):
    """Metodo per scaricare un singolo link."""
    try:
        async with session.get(url) as res:
            res.raise_for_status()

            # NOTA BENE: BeautifulSoup è necessario perché 'res' non ha .find()
            # Esempio di utilizzo assumendo che importi bs4:
            # text = await res.text()
            # soup = BeautifulSoup(text, 'html.parser')
            # cutoff = soup.find('h2', class_="Cutoffstyles__CutoffAmount-sc-ec7g4g-19 eLisKc")
            # scraped_data[url] = cutoff.text if cutoff else None

            # Per ora lasciamo la pseudologica
            pass

    except (asyncio.TimeoutError, aiohttp.ClientError) as e:
        print(f"[Cacher] Errore di rete su {url}: {e}")
    except Exception as e:
        print(f"[Cacher] Errore imprevisto su {url}: {e}")


async def generic_scraper_worker(urls: list[str], sleep_time: int):
    """Worker che esegue le richieste in parallelo e poi attende sleep_time."""
    async with aiohttp.ClientSession() as session:
        while True:
            # Crea e aspetta i task per url contemporaneamente
            tasks = [fetch_cutoff(session, url) for url in urls]
            await asyncio.gather(*tasks)

            # Timer di attesa (es. 3600s, 300s)
            await asyncio.sleep(sleep_time)


async def start_cutoff_tasks():
    """Funzione che inizializza e lancia i vari worker per i diversi timer."""
    # Gruppo timer 1 ora
    long_timer_urls = [Link.CUTOFF_GM.value, Link.CUTOFF_CH.value]

    # Gruppo timer 5 minuti (300 secondi)
    short_timer_urls = [
        Link.LINK_300_1.value,
        Link.LINK_300_2.value,
        Link.LINK_300_3.value,
        Link.LINK_300_4.value
    ]

    # eseguiamo in parallelo sia il worker da 3600 che quello da 300
    await asyncio.gather(
        generic_scraper_worker(long_timer_urls, 3600),
        generic_scraper_worker(short_timer_urls, 300)
    )