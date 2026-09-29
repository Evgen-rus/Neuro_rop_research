# C01v2 — CUSTOMER_FUTURE_ACTION_COMMITMENT

Unit: one clean customer utterance. Decide from its text alone. No deal context, outcome, prior labels, Jev output, or implied next steps.

**Question:** Does the customer explicitly commit themselves or another customer-side person/team to perform a concrete future action after this utterance?

**YES** requires all three: a customer-side actor (explicit or unambiguous first-person/customer team), a concrete action, and that action being future relative to this utterance. A deadline is optional. Examples: «Я завтра пришлю размеры», «Передам предложение директору и вернусь с ответом», «Инженер проверит образец», «Закупки свяжутся с вами», «Мы обсудим это на встрече и после неё дадим решение».

**NO** for a choice/preference/state without a future action («Остановимся на вакууме», «Этот вариант нам подходит», «Берём второй вариант»); mere information about a scheduled event («У нас завтра встреча», «На следующей неделе директор будет на месте»); vague intention or possibility («Посмотрим», «Подумаем», «Постараемся», «Наверное обсудим»); seller-owned action/request («Позвоните завтра», «Пришлите договор»); past action or waiting for someone else. «Надо обсудить с директором», «Планируем установить», «Будем смотреть», «Ждём инженера» are NO without an explicit concrete customer-side action commitment.

Output only YES or NO. Do not extract actor, action, or deadline. Freeze this contract before labeling.
