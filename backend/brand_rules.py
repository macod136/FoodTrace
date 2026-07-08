"""品牌名稱規則與產品品牌提取工具。

品牌不是原始 JSON 的獨立欄位，因此只收錄能從產品名稱或公司名稱
明確辨識的品牌。規則由上往下比對，較具體的品牌應放在較前面。
"""

from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class BrandRule:
    name: str
    product_keywords: tuple[str, ...] = ()
    company_keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class BrandDecision:
    name: str = ""
    source: str = "unknown"
    confidence: str = "unknown"
    matched_text: str = ""
    reason: str = "無法安全判定品牌"


BRAND_RULES = (
    # 人工確認的跨國／代理商品牌
    BrandRule("森文", ("森文",)),
    BrandRule("蛋小白", ("蛋小白",)),
    BrandRule("MANTOVA", ("MANTOVA", "Mantova")),
    BrandRule("Fazio", ("Fazio", "FAZIO")),
    BrandRule("旺來興", ("旺來興",)),
    # 統一企業及飲品／泡麵品牌
    BrandRule("來一客", ("來一客",)),
    BrandRule("純喫茶", ("純喫茶", "純吃茶")),
    BrandRule("茶裏王", ("茶裏王", "茶里王")),
    BrandRule("每朝健康", ("每朝健康",)),
    BrandRule("左岸咖啡館", ("左岸咖啡館",)),
    BrandRule("滿漢大餐", ("滿漢大餐",)),
    BrandRule("科學麵", ("科學麵",)),
    BrandRule("麥香", ("麥香",)),
    BrandRule("統一", ("統一",), ("統一企業",)),

    # 乳品、冰品與飲料
    BrandRule("杜老爺", ("杜老爺",)),
    BrandRule("林鳳營", ("林鳳營",)),
    BrandRule("瑞穗", ("瑞穗",)),
    BrandRule("福樂", ("福樂",)),
    BrandRule("光泉", ("光泉",), ("光泉牧場",)),
    BrandRule("味全", ("味全",), ("味全食品",)),
    BrandRule("義美", ("義美",), ("義美食品",)),
    BrandRule("原萃", ("原萃",)),
    BrandRule("御茶園", ("御茶園",)),
    BrandRule("舒跑", ("舒跑",)),
    BrandRule("貝納頌", ("貝納頌",)),
    BrandRule("伯朗", ("伯朗",)),
    BrandRule("黑松", ("黑松",), ("黑松股份",)),
    BrandRule("FIN", ("FIN", "Fin")),
    BrandRule("悅氏", ("悅氏",)),
    BrandRule("波蜜", ("波蜜",)),
    BrandRule("泰山", ("泰山",), ("泰山企業",)),
    BrandRule("愛之味", ("愛之味",), ("愛之味股份",)),

    # 調味品、沖泡食品與即食食品
    BrandRule("牛頭牌", ("牛頭牌",)),
    BrandRule("桂格", ("桂格",)),
    BrandRule("可果美", ("可果美",)),
    BrandRule("金蘭", ("金蘭",), ("金蘭食品",)),
    BrandRule("萬家香", ("萬家香",), ("萬家香醬園",)),
    BrandRule("工研", ("工研",), ("大安工研",)),
    BrandRule("味味一品", ("味味一品",)),
    BrandRule("王子麵", ("王子麵",)),
    BrandRule("維力", ("維力",), ("維力食品",)),
    BrandRule("味丹", ("味丹",), ("味丹企業",)),
    BrandRule("台酒", ("台酒", "臺酒",), ("臺灣菸酒", "台灣菸酒")),

    # 肉品、冷凍食品與零食
    BrandRule("黑橋牌", ("黑橋牌",), ("黑橋牌企業",)),
    BrandRule("新東陽", ("新東陽",), ("新東陽股份",)),
    BrandRule("桂冠", ("桂冠",), ("桂冠實業",)),
    BrandRule("奇美", ("奇美",), ("奇美食品",)),
    BrandRule("灣仔碼頭", ("灣仔碼頭",)),
    BrandRule("萬歲牌", ("萬歲牌",)),
    BrandRule("可樂果", ("可樂果",)),
    BrandRule("卡迪那", ("卡迪那",)),
    BrandRule("元本山", ("元本山",)),
    BrandRule("盛香珍", ("盛香珍",)),
    BrandRule("乖乖", ("乖乖",), ("乖乖股份",)),
    BrandRule("孔雀", ("孔雀",)),
    BrandRule("旺旺", ("旺旺",), ("旺旺食品",)),
    BrandRule("小美", ("小美",)),
    BrandRule("77乳加", ("77乳加", "七七乳加")),
    BrandRule("新貴派", ("新貴派",)),
    BrandRule("三商巧福", ("三商巧福",)),
    BrandRule("三商", (), ("三商行",)),
)


def _contains_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    text_casefold = text.casefold()
    return any(keyword.casefold() in text_casefold for keyword in keywords)


LEGAL_SUFFIXES = (
    "股份有限公司",
    "有限責任公司",
    "有限公司",
    "股份公司",
    "（股）公司",
    "(股)公司",
    "公司",
    "企業社",
    "實業社",
    "合作社",
    "商行",
    "商號",
    "Corporation",
    "Company Limited",
    "Co., Ltd.",
    "Co.,Ltd.",
    "Limited",
    "Ltd.",
)

BUSINESS_SUFFIXES = (
    "食品工業",
    "食品企業",
    "食品科技",
    "食品",
    "企業",
    "實業",
    "國際",
    "生物科技",
    "生技",
    "餐飲",
    "貿易",
    "工業",
    "農產",
    "製造",
    "醬園",
)

FACTORY_SUFFIX_PATTERN = re.compile(
    r"(?:台北|臺北|新北|桃園|新竹|苗栗|台中|臺中|彰化|南投|"
    r"雲林|嘉義|台南|臺南|高雄|屏東|宜蘭|花蓮|台東|臺東|澎湖)?"
    r"(?:第一|第二|一|二)?(?:製造)?(?:總)?廠$"
)


def derive_brand_from_company(company_name: str) -> str:
    """移除法人、業態與廠別字樣，從公司名稱取得後備品牌名。"""
    name = unicodedata.normalize("NFKC", company_name or "").strip()
    if not name:
        return ""

    name = re.sub(r"^[：:、,，.。\s]+|[：:、,，.。\s]+$", "", name)
    name = re.sub(r"(?:-|－)?(?:分公司|分店|營業所)$", "", name).strip()
    name = FACTORY_SUFFIX_PATTERN.sub("", name).strip()

    changed = True
    while changed:
        changed = False
        for suffix in LEGAL_SUFFIXES:
            if name.casefold().endswith(suffix.casefold()):
                name = name[: -len(suffix)].strip(" -－_()（）")
                changed = True
                break

    # 法人名稱後半部通常是業態，不是消費者看到的品牌。
    for suffix in BUSINESS_SUFFIXES:
        if name.endswith(suffix) and len(name) > len(suffix):
            name = name[: -len(suffix)].strip()
            break

    if name.startswith(("台灣", "臺灣")) and len(name) > 3:
        name = name[2:].strip()

    name = name.strip(" -－_()（）")
    if re.fullmatch(r"[A-Za-z]?-?[\d-]+", name):
        return ""
    if len(name) < 2 or not any(character.isalpha() for character in name):
        return ""
    return name


COUNTRY_PREFIXES = (
    "加拿大", "義大利", "意大利", "日本", "台灣", "臺灣", "澳洲",
    "美國", "紐西蘭", "新西蘭", "西班牙", "希臘", "法國", "德國",
    "英國", "韓國", "泰國", "越南", "荷蘭", "比利時", "瑞士", "葡萄牙",
)

GENERIC_BRAND_WORDS = {
    "蜂蜜", "酸梅", "冬瓜", "冷凍", "特級", "天然", "有機", "原味",
    "香草粉", "橄欖油", "沙拉醬", "芥花油", "葵花油", "調和油",
    "食品", "產品", "精選", "頂級", "優質", "新鮮", "即食", "低脂",
    "外銷", "停用", "預購", "切片", "含餡", "非基改", "奶素", "全素",
    "餐廳專用", "即食沖泡", "無味素", "品牌",
}

BRACKET_DENY_FRAGMENTS = (
    "香料", "餅乾", "外銷", "停用", "預購", "專用", "即食", "沖泡",
    "非基改", "無味素", "原味+", "奶素", "全素", "含餡", "切片",
)

NON_BRAND_COMPANY_KEYWORDS = {
    "百貨", "友士", "分公司", "香港商", "新加坡商", "進口", "代理",
    "洋行", "貿易", "家樂福", "大潤發", "好市多", "惠康", "全聯",
    "美廉社", "新光三越", "太平洋崇光", "遠東SOGO", "大北化工",
}

ENGLISH_DENY = {
    "L", "D", "DL", "PH", "KCAL", "ML", "G", "KG", "MG", "CC",
    "NO", "NEW", "FOOD", "FOODS", "PRODUCT", "USA",
    "PROPYLENE", "SODIUM", "OEM", "CAS", "MCT", "CHOICE",
    "PREMIUM", "NATURAL", "JASMINE", "GREEN", "BLACK", "MILK",
    "CHOCOLATE", "CARNAUBA", "BCAA", "PDO",
    "DIY", "JAPANESE", "GOOD", "HEALTH", "ASSAM", "KERIPIK",
    "BASA", "CHLORELLA",
}

BRAND_ALIASES = {
    "mantova": "MANTOVA",
    "fazio": "Fazio",
    "bristot": "BRISTOT",
    "clemente": "CLEMENTE",
    "a-bao": "A-BAO",
    "純吃茶": "純喫茶",
}


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").strip()
    return re.sub(r"\s+", " ", value)


def canonical_brand_name(value: str) -> str:
    value = normalize_text(value).strip(" -－_()（）[]【】")
    return BRAND_ALIASES.get(value.casefold(), value)


def _is_non_brand_company(company_name: str, derived_company: str) -> bool:
    text = f"{normalize_text(company_name)} {derived_company}"
    return any(keyword.casefold() in text.casefold() for keyword in NON_BRAND_COMPANY_KEYWORDS)


def _valid_candidate(candidate: str) -> bool:
    candidate = canonical_brand_name(candidate)
    if not 2 <= len(candidate) <= 24:
        return False
    if candidate in GENERIC_BRAND_WORDS:
        return False
    if re.fullmatch(r"[\d\W_]+", candidate):
        return False
    return True


def _valid_english_candidate(candidate: str) -> bool:
    """Conservatively reject product codes and generic English terms."""
    if any(character.isdigit() for character in candidate):
        return False
    if candidate.upper() in ENGLISH_DENY:
        return False
    return _valid_candidate(candidate)


def extract_brand_decision(company_name: str, product_name: str) -> BrandDecision:
    """以準確率優先，回傳品牌、來源、信心與判定原因。"""
    product_name = normalize_text(product_name)
    company_name = normalize_text(company_name)

    for rule in BRAND_RULES:
        if _contains_keyword(product_name, rule.product_keywords):
            return BrandDecision(
                rule.name, "manual_rule", "high", rule.name,
                "產品名稱命中人工確認品牌規則",
            )

    for rule in BRAND_RULES:
        if _contains_keyword(company_name, rule.company_keywords):
            return BrandDecision(
                rule.name, "company_verified", "high", rule.name,
                "公司名稱命中人工確認品牌規則",
            )

    bracket_match = re.match(r"^[【\[]\s*([^】\]]+?)\s*[】\]]", product_name)
    if bracket_match:
        candidate = canonical_brand_name(bracket_match.group(1))
        for country in COUNTRY_PREFIXES:
            if candidate.startswith(country):
                candidate = candidate[len(country):].strip(" ：:")
                break
        if (
            len(candidate) <= 16
            and not any(character.isdigit() for character in candidate)
            and not any(word in candidate for word in BRACKET_DENY_FRAGMENTS)
            and _valid_candidate(candidate)
        ):
            return BrandDecision(
                candidate, "bracket", "high", bracket_match.group(0),
                "品名開頭使用明確品牌括號",
            )

    country_pattern = "|".join(map(re.escape, COUNTRY_PREFIXES))
    english_match = re.match(
        rf"^(?:(?:{country_pattern})\s*)?([A-Za-z][A-Za-z0-9&.'-]{{1,23}})",
        product_name,
    )
    if english_match:
        candidate = canonical_brand_name(english_match.group(1))
        remaining_text = product_name[english_match.end():]
        has_unparsed_english_word = bool(re.match(r"\s+[A-Za-z]", remaining_text))
        if (
            len(candidate) >= 3
            and not has_unparsed_english_word
            and _valid_english_candidate(candidate)
        ):
            return BrandDecision(
                candidate, "english_prefix", "high", english_match.group(1),
                "品名開頭含可信英文品牌候選",
            )

    derived_company = derive_brand_from_company(company_name)
    company_is_non_brand = _is_non_brand_company(company_name, derived_company)
    if derived_company and not company_is_non_brand and derived_company in product_name:
        return BrandDecision(
            derived_company, "company_verified", "medium", derived_company,
            "品名明確包含清洗後公司名稱",
        )

    if derived_company and not company_is_non_brand:
        return BrandDecision(
            derived_company, "company_fallback", "low", derived_company,
            "品名無可靠品牌特徵，僅提供公司備用名稱",
        )

    return BrandDecision()


def extract_brand(company_name: str, product_name: str) -> str:
    """相容舊呼叫端；只回傳已確認品牌，不混入公司 fallback。"""
    decision = extract_brand_decision(company_name, product_name)
    return decision.name if decision.source != "company_fallback" else ""


def assign_brands(products: list[dict]) -> list[dict]:
    """加入正式品牌與可稽核的判定資訊。"""
    decisions = [
        extract_brand_decision(
            product.get("company_name", ""),
            product.get("product_name", ""),
        )
        for product in products
    ]
    english_support = {}
    for decision in decisions:
        if decision.source == "english_prefix":
            english_support[decision.name] = english_support.get(decision.name, 0) + 1

    for product, original_decision in zip(products, decisions):
        decision = original_decision
        if (
            decision.source == "english_prefix"
            and english_support.get(decision.name, 0) < 2
        ):
            company_name = product.get("company_name", "")
            derived_company = derive_brand_from_company(company_name)
            if derived_company and not _is_non_brand_company(
                company_name, derived_company
            ):
                decision = BrandDecision(
                    derived_company,
                    "company_fallback",
                    "low",
                    derived_company,
                    "英文候選僅出現一次，降級為公司備用名稱",
                )
            else:
                decision = BrandDecision(
                    reason="英文候選僅出現一次且公司不可作為備用品牌"
                )
        product["brand_name"] = (
            decision.name if decision.source != "company_fallback" else ""
        )
        product["brand_fallback_name"] = (
            decision.name if decision.source == "company_fallback" else ""
        )
        product["brand_source"] = decision.source
        product["brand_confidence"] = decision.confidence
        product["brand_matched_text"] = decision.matched_text
        product["brand_reason"] = decision.reason
    return products


BRAND_NAMES = tuple(rule.name for rule in BRAND_RULES)


