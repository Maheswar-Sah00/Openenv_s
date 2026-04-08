"""Generate data/scam_dataset.json — curated synthetic scenarios + validation."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    rows: list[dict] = []

    def add(**kwargs: object) -> None:
        rows.append(dict(kwargs))

    # --- Easy scams (obvious) ---
    easy_scam_templates = [
        ("Your KYC expired. Send OTP immediately to avoid blocking.", "kyc", True, 0.95),
        ("URGENT: Click http://bit.ly/fakebank to verify your account.", "phishing", True, 0.9),
        ("Dear user, your ATM card is blocked. Share CVV to unlock.", "phishing", False, 0.85),
        ("You won Rs 5 lakh! Pay processing fee via UPI to claim.", "investment", False, 0.8),
        ("NetBanking access suspended. Reply with MPIN to restore.", "phishing", False, 0.92),
        ("Your account will be debited in 1 hour unless you confirm OTP here.", "otp", False, 0.88),
        ("HDFC Security: unusual login. Verify at hdfc-secure-login.xyz", "phishing", True, 0.87),
        ("SBI: Your YONO session expired. Enter OTP to continue.", "impersonation", False, 0.9),
        ("Income Tax refund pending. Submit bank details on itrefund.co.in", "phishing", True, 0.82),
        ("Your wallet will be closed. Send Aadhaar OTP now.", "kyc", False, 0.91),
        ("Crypto doubling: send 1 ETH get 2 back in 10 minutes.", "investment", True, 0.78),
        ("WhatsApp: Your payment failed. Tap wa.me/fakepay to fix.", "phishing", True, 0.84),
        ("Amazon: Order on hold. Confirm payment link amzn-security.ru", "phishing", True, 0.83),
        ("IRCTC: Ticket cancelled unless you pay rebooking fee via link.", "phishing", True, 0.8),
        ("Paytm KYC incomplete. Share OTP to complete in 30 minutes.", "kyc", False, 0.89),
        ("Your credit score dropped. Pay Rs 499 to fix instantly.", "scam_fee", True, 0.76),
        ("FedEx: Package held at customs. Pay duty at fake-fedex.net", "phishing", True, 0.81),
        ("LinkedIn: Someone viewed your profile 50 times. Click to see.", "phishing", True, 0.7),
        ("Your SIM will be deactivated. Send last 4 digits of Aadhaar.", "phishing", False, 0.86),
        ("Bank server upgrade: validate credentials on secure-portal.tk", "phishing", True, 0.88),
    ]
    for i, (msg, tag, link, urg) in enumerate(easy_scam_templates, start=1):
        add(
            id=f"easy_scam_{i:02d}",
            difficulty="easy",
            true_label="scam",
            channel="sms" if i % 2 else "email",
            language="en" if i % 3 else "hinglish",
            sender_type="unknown",
            message=msg,
            messages=[msg],
            link_present=link,
            urgency_score=urg,
            tags=[tag, "easy"],
        )

    easy_scam_variants = [
        ("RBI Notice: Your PAN is linked to suspicious UPI. Validate on rbisecure.in now.", True, 0.93),
        ("Electricity dept: Bill unpaid. Pay Rs 2,499 via link or power cut in 2 hours.", True, 0.9),
        ("DHL: Customs hold on parcel. Pay clearance fee to dhl-track-support.net", True, 0.84),
        ("Job offer: Work from home, earn 50k/week. Pay registration Rs 999 first.", False, 0.77),
        ("Your Netflix payment failed. Update card on netflix-billing-support.com", True, 0.82),
        ("WINNER! You got iPhone 15 in lucky draw. Pay GST Rs 2,500 to claim.", False, 0.8),
        ("Aadhaar eKYC failed. Re-verify on uidai-helpdesk.co to avoid SIM block.", True, 0.91),
        ("SEBI alert: Your demat will freeze. Confirm PAN on sebi-verifyportal.xyz", True, 0.86),
        ("Mother needs surgery funds urgently — wrong account sent, please refund to this UPI.", False, 0.88),
        ("Your Flipkart refund of Rs 1,200 is pending. Approve on flipkart-refund.co", True, 0.83),
        ("Instagram: Copyright strike on your reel. Appeal within 24h at meta-appeals.io", True, 0.74),
        ("Truecaller Premium renewal failed. Tap tc-premium-billing.ru to fix.", True, 0.72),
        ("Gas subsidy credited. Claim Rs 3,200 on pm-subsidy-portal.in (last date today).", True, 0.85),
        ("Your child’s school fee link expired. Pay immediately on schoolpay-verify.com", True, 0.79),
        ("Bank merger: re-KYC mandatory. Complete on merger-kyc-bank.net by tonight.", True, 0.9),
    ]
    for j, (msg, link, urg) in enumerate(easy_scam_variants, start=21):
        add(
            id=f"easy_scam_{j:02d}",
            difficulty="easy",
            true_label="scam",
            channel="whatsapp" if j % 4 == 0 else "sms",
            language="en" if j % 3 else "hinglish",
            sender_type="unknown",
            message=msg,
            messages=[msg],
            link_present=link,
            urgency_score=urg,
            tags=["phishing", "easy", "variant"],
        )

    easy_scam_subtle = [
        ("Reminder: Your free trial ends tomorrow. Add card on billing-portal-now.net to avoid loss of data.", True, 0.62),
        ("We noticed login from Windows PC. If this was you, no action needed.", False, 0.45),
        ("Security check: confirm your mobile number is still +91-XXXXXX7890 by tapping link.", True, 0.7),
        ("Your reward points expire in 48 hours. Redeem on rewards-bank-partner.co", True, 0.66),
        ("Voice mailbox full. Listen to urgent bank voicemail: call this premium-rate number.", False, 0.72),
        ("Linked bank account sync failed. Re-link on upi-sync-verify.in", True, 0.81),
        ("Minor statement mismatch of Rs 1.00 — confirm via link to avoid freeze.", True, 0.74),
        ("Your cheque book dispatch delayed. Track on cheque-dispatch-fake.com", True, 0.69),
        ("NEFT return: beneficiary name mismatch. Fix on neft-correction-portal.net", True, 0.77),
        ("ATM card found at branch. Claim by paying courier fee via UPI.", False, 0.71),
        ("Loan pre-closure quote generated. Pay processing fee to download PDF.", True, 0.78),
        ("CIBIL score updated. View full report on cibil-free-score.in", True, 0.73),
        ("International roaming pack activated without request. Cancel via roaming-cancel.ru", True, 0.68),
        ("Your UPI PIN will expire. Reset on pin-reset-upi.co", True, 0.89),
        ("Bank holiday list 2026 attached. Open macro-enabled Excel from link.", True, 0.64),
    ]
    for n, (msg, link, urg) in enumerate(easy_scam_subtle, start=36):
        add(
            id=f"easy_scam_{n:02d}",
            difficulty="easy",
            true_label="scam",
            channel="email" if n % 3 == 0 else "sms",
            language="en",
            sender_type="unknown",
            message=msg,
            messages=[msg],
            link_present=link,
            urgency_score=urg,
            tags=["phishing", "easy", "subtle"],
        )

    # Easy legitimate
    easy_legit = [
        "Your salary of INR 85,000 has been credited to A/c XX1234.",
        "Reminder: EMI of Rs 12,400 due on 10th. Pay via official app only.",
        "Your debit card ending 4242 was used at SWIGGY for Rs 320.",
        "NetBanking: Scheduled transfer of Rs 5,000 to Rahul completed.",
        "Welcome to mobile banking. Download the official app from Play Store.",
        "Your FD receipt is available in the secure inbox of internet banking.",
        "Loan statement for March generated. Login to official portal to view.",
        "UPI payment of Rs 150 to ZOMATO successful. Ref: 998877.",
        "Your meeting with branch manager is confirmed for Tuesday 3 PM.",
        "Security tip: Never share OTP. Bank staff will never ask for it.",
    ]
    for i, msg in enumerate(easy_legit, start=1):
        add(
            id=f"easy_legit_{i:02d}",
            difficulty="easy",
            true_label="legitimate",
            channel="email" if i % 2 else "in_app",
            language="en",
            sender_type="bank_official",
            message=msg,
            messages=[msg],
            link_present=False,
            urgency_score=0.2 + (i % 5) * 0.05,
            tags=["legitimate", "easy"],
        )

    easy_legit_unknown = [
        ("Blinkit: Your order #8821 arrives by 8 PM. Show the in-app rider code only on your phone.", "delivery_partner", 0.35),
        ("Swiggy: Rider is nearby. Never share your delivery PIN outside the Swiggy app.", "delivery_partner", 0.3),
        ("IRCTC: PNR confirmed. Ticket details in official app only. No payment link via SMS.", "service_provider", 0.25),
        ("Government: GST filing reminder for GSTR-3B due date. File on gst.gov.in portal only.", "government_notice", 0.4),
        ("Airtel: Data pack renewed. For queries use 121 or official app.", "telco_official", 0.22),
        ("NPS: Contribution of Rs 5,000 received for PRAN XX****12. Statement in CRA login.", "pension_authority", 0.28),
    ]
    for i, (msg, stype, urg) in enumerate(easy_legit_unknown, start=1):
        add(
            id=f"easy_legit_u_{i:02d}",
            difficulty="easy",
            true_label="legitimate",
            channel="sms",
            language="en",
            sender_type=stype,
            message=msg,
            messages=[msg],
            link_present=False,
            urgency_score=urg,
            tags=["legitimate", "easy", "unknown_brand_ok"],
        )

    # Medium: two-part social engineering
    medium_pairs = [
        (
            "Hello, I am calling from SBI support regarding your account activity.",
            "Our system shows an unverified device login. Please confirm you received this SMS.",
        ),
        (
            "This is ICICI fraud desk. We noticed a suspicious UPI attempt.",
            "To secure your account, do not share OTP; we only need you to acknowledge this alert.",
        ),
        (
            "Axis Bank priority support: unusual transaction flagged.",
            "If this was not you, we recommend warning any joint account holders immediately.",
        ),
        (
            "Kotak 811: We could not reach you on call about a high-value transfer.",
            "Reply only if you initiated a transfer above Rs 50,000 in the last hour.",
        ),
        (
            "HDFC: Potential phishing attempt detected on your registered email.",
            "Please verify sender identity using official app chat before clicking any links.",
        ),
        (
            "Federal Bank: New beneficiary added from unknown IP.",
            "If you did not add this beneficiary, warn your family and contact branch.",
        ),
        (
            "Bandhan Bank: SIM swap alert on your registered mobile.",
            "We have paused high-risk transactions until you verify identity in branch or app.",
        ),
        (
            "IDFC FIRST: Credit card used abroad while phone location shows India.",
            "Confirm travel or warn user via registered channels — do not use links in SMS.",
        ),
    ]
    for i, (m1, m2) in enumerate(medium_pairs, start=1):
        add(
            id=f"medium_scam_{i:02d}",
            difficulty="medium",
            true_label="scam",
            channel="sms",
            language="en" if i % 2 else "hinglish",
            sender_type="unknown",
            message=m1,
            messages=[m1, m2],
            link_present=False,
            urgency_score=0.55 + i * 0.02,
            tags=["impersonation", "social_engineering"],
        )

    medium_scam_extra = [
        (
            "BOB World: We detected a login from a new city.",
            "If this was not you, warn linked family accounts and call 1800-XXX from number printed on your card.",
        ),
        (
            "PNB: UPI collect request spike on your account.",
            "Do not approve unknown requests. Acknowledge if you want us to pause UPI temporarily.",
        ),
        (
            "Union Bank: Salary credit reversal risk due to name mismatch.",
            "Please verify with HR; meanwhile warn beneficiaries of delayed transfers.",
        ),
        (
            "Yes Bank: Premium card used at high-risk merchant category.",
            "Confirm purchase or warn household cards on same profile.",
        ),
        (
            "IndusInd: Device binding changed for mobile banking.",
            "If unexpected, warn joint holders and visit branch with ID.",
        ),
        (
            "RBL: International POS attempt while card is domestic-only.",
            "Reply ONLY if you are traveling; otherwise warn and block via app.",
        ),
        (
            "CSB Bank: Net banking password reset initiated from new browser.",
            "Warn anyone with access to your email; we never ask for OTP on call.",
        ),
    ]
    for idx, (m1, m2) in enumerate(medium_scam_extra, start=9):
        add(
            id=f"medium_scam_{idx:02d}",
            difficulty="medium",
            true_label="scam",
            channel="sms",
            language="en" if idx % 2 else "hinglish",
            sender_type="unknown",
            message=m1,
            messages=[m1, m2],
            link_present=False,
            urgency_score=0.58 + (idx % 5) * 0.02,
            tags=["impersonation", "bank_brand_spoof"],
        )

    medium_legit = [
        (
            "Your branch relationship manager will call from official 1800 number today.",
            "No action needed if you did not request a callback.",
        ),
        (
            "Annual privacy notice: how we use your data is updated on our website.",
            "Log in to the official site only; ignore forwarded PDFs claiming to be us.",
        ),
    ]
    for i, (m1, m2) in enumerate(medium_legit, start=1):
        add(
            id=f"medium_legit_{i:02d}",
            difficulty="medium",
            true_label="legitimate",
            channel="email",
            language="en",
            sender_type="bank_official",
            message=m1,
            messages=[m1, m2],
            link_present=True,
            urgency_score=0.25,
            tags=["legitimate"],
        )

    # Hard: multi-step attack chains
    hard_chains = [
        [
            "Hi, your salary credit is delayed due to payroll sync. We will update shortly.",
            "Please confirm your employee ID by replying YES to validate HR records.",
            "Now share the OTP you received to complete HR verification.",
        ],
        [
            "Netflix: Payment failed for renewal.",
            "Update payment on our secure page within 24h.",
            "Enter OTP from bank to authorize Rs 649 debit.",
        ],
        [
            "Courier: Package arriving today. Track with reference 8821.",
            "Customs fee Rs 499 required — pay via link for express clearance.",
            "Urgent: OTP needed to release shipment or it will be returned.",
        ],
        [
            "Investment tip: Bluechip fund up 12% this quarter.",
            "Open demat on partner portal to get free research.",
            "Transfer token amount via UPI to activate premium alerts.",
        ],
        [
            "Bank: Low balance alert on salary account.",
            "Quick loan pre-approved — tap to see offer (no OTP needed to view).",
            "To disburse, confirm OTP sent to mobile for Rs 1 verification debit.",
        ],
        [
            "Govt subsidy scheme: you are eligible for LPG cashback.",
            "Upload bank proof on portal (official-looking domain).",
            "Final step: share OTP to link Aadhaar for instant credit.",
        ],
        [
            "Friend hi, wrong number pe message aa gaya — delete mat karna.",
            "Actually I need small help, bank server down hai.",
            "Mere ko OTP forward kar do, main tumhara recharge kar dunga.",
        ],
        [
            "HR: Please join new attendance app before Monday.",
            "Use temp password Attend2024!",
            "Sync bank for payroll — enter OTP when prompted to verify account.",
        ],
    ]
    stage_sets = [
        ["lure", "harvest", "pressure"],
        ["lure", "harvest", "pressure"],
        ["lure", "harvest", "pressure"],
        ["lure", "harvest", "pressure"],
        ["lure", "harvest", "pressure"],
        ["lure", "harvest", "pressure"],
        ["lure", "harvest", "pressure"],
        ["lure", "harvest", "pressure"],
    ]
    for i, (msgs, stages) in enumerate(zip(hard_chains, stage_sets), start=1):
        add(
            id=f"hard_scam_{i:02d}",
            difficulty="hard",
            true_label="scam",
            channel="whatsapp" if i % 3 == 0 else "sms",
            language="en" if i != 7 else "hinglish",
            sender_type="unknown",
            message=msgs[0],
            messages=msgs,
            link_present=True,
            urgency_score=0.65 + 0.03 * i,
            tags=["multi_step", "otp"],
            stage_labels=stages,
            otp_message_index=2,
        )

    hard_scam_extra_chains = [
        [
            "Team: Standup notes for today attached (no action needed).",
            "IT: Please approve MFA push for new VPN profile (looks like routine SSO).",
            "IT-Helpdesk: Enter the OTP shown in email to finish VPN setup — urgent before audit.",
        ],
        [
            "Utility bill autopay succeeded for March. Thank you.",
            "Correction: duplicate debit detected. Refund will be processed after OTP confirmation.",
            "Send OTP you receive from bank to this thread to speed up refund.",
        ],
        [
            "Dating app match: Hi! I trade forex part-time, happy to share tips.",
            "I can guide you on Binance — first deposit small USDT to test withdrawal.",
            "Share your wallet seed screenshot privately so I can check if your wallet is compatible.",
        ],
        [
            "Zoom: Meeting invite updated — join link unchanged.",
            "Host requests pre-install of remote support plugin for screen share.",
            "Run AnyDesk quick support code 9 8 7 6 5 so we can fix your audio driver.",
        ],
        [
            "Charity: Thank you for donating Rs 500 last month.",
            "Matching grant: double impact if you add Rs 500 via UPI collect request.",
            "UPI collect sent — approve and share transaction OTP for receipt automation.",
        ],
    ]
    for k, msgs in enumerate(hard_scam_extra_chains, start=9):
        add(
            id=f"hard_scam_{k:02d}",
            difficulty="hard",
            true_label="scam",
            channel="whatsapp" if k % 2 == 0 else "sms",
            language="en",
            sender_type="unknown",
            message=msgs[0],
            messages=msgs,
            link_present=True,
            urgency_score=0.68 + 0.02 * k,
            tags=["multi_step", "social_engineering"],
            stage_labels=["lure", "harvest", "pressure"],
            otp_message_index=2,
        )

    for i in range(1, 6):
        add(
            id=f"hard_legit_{i:02d}",
            difficulty="hard",
            true_label="legitimate",
            channel="in_app",
            language="en",
            sender_type="bank_official",
            message=f"Secure message thread {i}: loan discussion continues.",
            messages=[
                f"Secure message thread {i}: loan discussion continues.",
                "Please upload documents only inside the mobile banking secure vault.",
                "No OTP is required for document upload; ignore any SMS asking for OTP.",
            ],
            link_present=False,
            urgency_score=0.35,
            tags=["legitimate"],
            stage_labels=["info", "info", "info"],
            otp_message_index=None,
        )

    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from validate_dataset import assert_dataset_ok

    assert_dataset_ok(rows)

    out = Path(__file__).resolve().parent.parent / "data" / "scam_dataset.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(rows)} validated scenarios to {out}")


if __name__ == "__main__":
    main()
