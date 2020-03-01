#pragma once

class Bell
{
public:
    Bell(uint8_t outputPin)
    : mOutputPin(outputPin), mDinging(false)
    {
    }

    void Setup()
    {
        pinMode(mOutputPin, OUTPUT);

        digitalWrite(mOutputPin, LOW);
    }

    void Ding()
    {
        if (!mDinging)
        {
            mDinging = true;
            mDingRequestTime = 0;
        }
    }

    void Update()
    {
        if (mDinging)
        {
            unsigned long now = micros();
            if (mDingRequestTime == 0)
            {
                mDingRequestTime = now;
            }

            if (now - mDingRequestTime < DING_ACTUATION_MICROS)
            {
                digitalWrite(mOutputPin, HIGH);
            }
            else
            {
                digitalWrite(mOutputPin, LOW);
                mDinging = false;
            }
        }
    }

private:
    static constexpr unsigned long DING_ACTUATION_MICROS = 20000;

    uint8_t const mOutputPin;
    bool mDinging;
    unsigned long mDingRequestTime;
};