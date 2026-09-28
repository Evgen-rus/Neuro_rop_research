# C01 — CUSTOMER_CONCRETE_COMMITMENT

Unit: one clean, customer-authored utterance. Label only what the utterance explicitly says; do not use surrounding events, attachments, deal history, or outcome.

**Question:** Does this customer utterance explicitly commit the customer or a customer-side person/team to a concrete future action?

**YES:** Both a customer-side owner (explicit or an unambiguous first-person/customer-team subject) and a specific future action are present. The action must be asserted as something the owner will do, rather than merely considered. A deadline helps but is not required. Examples: «Я завтра пришлю размеры», «Передам КП директору и дам ответ», «Инженер проверит образец», «Закупки свяжутся с вами после согласования».

**NO:** No explicit customer-side commitment to a concrete future action. Generic intention, possibility, a wish or need to discuss, tentative effort without commitment, past action, awaiting another person's decision, interest, and requests that the seller act are NO. Examples: «Посмотрим», «Подумаем», «Возможно на следующей неделе», «Надо обсудить», «Позвоните завтра», «Интересно», «Постараемся прислать», «Надо будет посмотреть», «Давайте вернёмся позже», «Я передал коллегам», «Жду решения руководства».

Do not extract owner, action, or deadline fields. Output only YES or NO.
