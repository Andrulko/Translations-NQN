from typing import Callable, Union, Dict, Awaitable, Optional
import i18n
import pathlib
import copy
from discord import Guild
from discord.ext.commands import Context
from ._create_owo import create_owo
from ._ruamel_loader import YamlLoader


try:
    from prometheus_client import Counter
except ImportError:
    translate_function = None
else:
    keys_used = Counter(
        "keys_used",
        "Translation keys used",
        labelnames=["key"],
        namespace="translation"
    )
    def translate_function(key, **kwargs):
        keys_used.labels(key=key).inc()
        return i18n.t(key, **kwargs)


class Translator:
    locales = {
        "en": "en",
        "gb": "en",
        "us": "en",
        "uk": "en",
        "de": "de",
        "es": "es",
        "ru": "ru",
        "hi": "hi",
        "fr": "fr",
        "pt": "pt",
        "br": "pt",
        "ms": "ms",
        "it": "it",
        "vi": "vi",
        "fa": "fa"
    }

    locale_flags = {
        "en": "gb",
        "es": "es",
        "ru": "ru",
        "pt": "br",
        "it": "it",
        "vi": "vn",
        "fa": "ir"
    }

    flag_emojis = {locale: "".join(chr(0x1f185+ord(c)) for c in flag_name) for locale, flag_name in locale_flags.items()}
    hidden_locales = ["owo", "hi", "fr", "ms"]
    supported_locales = {*locales.values(), *hidden_locales}

    def __init__(self, get_locale: Optional[Callable[[Guild], Awaitable[str]]]):
        self.get_locale = get_locale
        root_path = pathlib.Path(__file__).parent
        i18n.load_path.append(root_path.absolute())
        i18n.set("enable_memoization", True)
        i18n.set("skip_locale_root_data", True)
        i18n.resource_loader.register_loader(YamlLoader, ["yml"])

        for path in root_path.rglob("*.yml"):
            locale = path.parent.name
            translations_dic = i18n.resource_loader.load_resource(str(path), None)
            i18n.resource_loader.load_translation_dic(translations_dic, "", locale)

        create_owo()
        if translate_function:
            self.translate_function = translate_function
        else:
            self.translate_function = i18n.t

    def add_locale_commands(self, bot):
        for locale in self.supported_locales:
            def inner(locale: str):
                async def run_locale(ctx, *, rest):
                    await bot.process_commands(ctx.message, ctx.prefix, rest, locale_override=locale)
                return run_locale
            bot.command(hidden=True, name=locale)(inner(locale))

    async def setup_translation(self, ctx: Context, guild_locale: str = None):
        if guild_locale is None:
            try:
                guild_locale = ctx.guild_settings.locale
            except AttributeError:
                pass
            if guild_locale is None:
                guild_locale = await self.get_locale(ctx.guild)
        defaults = {
            "locale": guild_locale.strip(" "),
            "locale_flag_emojis": " ".join(self.flag_emojis.values())
        }

        return TranslatorWithContext(defaults, lambda: ctx.command.module, translate_function=self.translate_function)

    def with_scope(self, scope: str, locale: str) -> "TranslatorWithContext":
        return TranslatorWithContext({"locale": locale}, scope=scope, translate_function=self.translate_function)

    def __call__(self, main_scope: str, guild: Union[Guild, str]):
        async def inner():
            if isinstance(guild, str):
                defaults = {
                    "locale": guild.strip(" "),
                    "locale_flag_emojis": " ".join(self.flag_emojis.values())
                }
            else:
                locale = await self.get_locale(guild)
                defaults = {
                    "locale": locale.strip(" "),
                    "locale_flag_emojis": " ".join(self.flag_emojis.values())
                }

            return TranslatorWithContext(defaults, main_scope, translate_function=self.translate_function)
        return inner()


class TranslatorWithContext:
    def __init__(self, defaults: Dict[str, str], scope: Union[str, Callable[[], str]], translate_function):
        self.defaults = defaults
        if isinstance(scope, str):
            self.scope = lambda: scope
        else:
            self.scope = scope
        self._translate_function = translate_function

    def set_locale(self, locale: str) -> "TranslatorWithContext":
        self.defaults["locale"] = locale
        return self

    def set_scope(self, scope: str) -> "TranslatorWithContext":
        self.scope = lambda: scope
        return self

    def __call__(self, text: str, scope: str = "", **kwargs):
        return self._translate_function(f"{scope or self.scope()}.{text}", **{**self.defaults, **kwargs})

    def __enter__(self):
        return copy.deepcopy(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
