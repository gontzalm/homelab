from string import Template

from ._models import ActivityType

NOTIFICATION_TEMPLATE: dict[ActivityType, Template] = {
    ActivityType.BUY: Template(
        "${date} -> 🟢 ${type}: +${quantity} ${symbol} @ ${unitPrice} ${currency}"
    ),
    ActivityType.SELL: Template(
        "${date} -> 🔴 ${type}: -${quantity} ${symbol} @ ${unitPrice} ${currency}"
    ),
    ActivityType.DIVIDEND: Template(
        "${date} -> 💰 ${type} ${symbol}: ${quantity} uds @ ${unitPrice} ${currency}"
    ),
    ActivityType.FEE: Template("${date} -> 💸 ${type} ${symbol} -${fee} ${currency}"),
    ActivityType.INTEREST: Template(
        "${date} -> 🌱 ${type} ${symbol} +${quantity} units (${comment})"
    ),
    ActivityType.LIABILITY: Template(
        "${date} -> 📉 ${type} ${symbol} Val: ${unitPrice} ${currency} | ${comment}"
    ),
}
