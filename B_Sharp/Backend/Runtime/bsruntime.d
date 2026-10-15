/**
 * B# Phase-1 D runtime: explicit helpers reproducing B# interpreter semantics
 * where D operators differ. Covers: true division, truncating integer
 * division/remainder with two's-complement wrap, exact integer power,
 * numeric casts (trunc/NaN/inf/wrap), Python-compatible float rendering,
 * string repeat, __to_String/__format/__writeln rendering.
 *
 * Out of scope (later phases): error codes (helpers abort loudly instead),
 * !pragma precision, containers, structs, imports, try/catch.
 */
module bsruntime;

import std.conv : to, parse, ConvException;
import std.format : format;
import std.math : isNaN, isInfinity, trunc, pow, fmod;
import std.stdio : stderr;

// Abort loudly on a runtime failure (e.g. division by zero). B# error-code
// parity (RUN100, ...) is a Phase-5 concern; never return a wrong value.
void bsFail(string msg)
{
    stderr.writeln("B# runtime error: ", msg);
    import core.stdc.stdlib : exit;

    exit(1);
}

// ---- Python-compatible float rendering (B# str()/repr() semantics) ----

private bool _needsDot(string t)
{
    import std.string : indexOf;

    return t.indexOf('.') < 0 && t.indexOf('e') < 0 && t.indexOf('E') < 0
        && t.indexOf('n') < 0 && t.indexOf('i') < 0;
}

/// Shortest round-tripping decimal for a double, mirroring Python repr().
string bsDblStr(double v)
{
    if (isNaN(v))
        return "nan";
    if (isInfinity(v))
        return v < 0 ? "-inf" : "inf";
    foreach (p; 1 .. 18)
    {
        string t = format("%.*g", p, v);
        try
        {
            string rest = t;
            double back = parse!double(rest);
            if (rest.length == 0 && back == v)
                return _needsDot(t) ? t ~ ".0" : t;
        }
        catch (ConvException)
        {
        }
    }
    string t = format("%.17g", v);
    return _needsDot(t) ? t ~ ".0" : t;
}

/// Shortest round-tripping decimal for a float, mirroring f32_repr().
/// NOTE: unlike doubles, B# does NOT force a trailing ".0" here.
string bsFltStr(float v)
{
    if (isNaN(v))
        return "nan";
    if (isInfinity(v))
        return v < 0 ? "-inf" : "inf";
    foreach (p; 1 .. 10)
    {
        string t = format("%.*g", p, v);
        try
        {
            string rest = t;
            float back = parse!float(rest);
            if (rest.length == 0 && back == v)
                return t;
        }
        catch (ConvException)
        {
        }
    }
    return format("%.9g", v);
}

// ---- Arithmetic ----

/// B# `/`: true division, always Double, RUN100 on zero.
double bsDiv(T, U)(T a, U b)
{
    static if (is(T == bool) || is(U == bool))
        static assert(false, "bsDiv on Bool");
    if (cast(double) b == 0.0)
        bsFail("division by zero");
    return cast(double) a / cast(double) b;
}

private ulong _uabs(T)(T v)
{
    static if (is(T == ulong))
        return v;
    else static if (is(T == long))
        return v < 0 ? cast(ulong)(-(v + 1)) + 1UL : cast(ulong) v;
    else static if (is(T == uint))
        return v;
    else static if (is(T == int))
        return v < 0 ? cast(ulong)(-(v + 1)) + 1U : cast(ulong) v;
    else static if (is(T == ushort))
        return v;
    else static if (is(T == short))
        return v < 0 ? cast(ushort)(-(v + 1)) + 1U : cast(ushort) v;
    else static if (is(T == ubyte))
        return v;
    else static if (is(T == byte))
        return v < 0 ? cast(ubyte)(-(v + 1)) + 1U : cast(ubyte) v;
    else
        static assert(false, "non-integer bsIdiv/bsMod operand");
}

/// B# `%`: C-style truncating integer division with wrap (MIN/-1 wraps).
T bsIdiv(T)(T a, T b)
{
    if (b == 0)
        bsFail("integer division by zero");
    ulong ua = _uabs(a), ub = _uabs(b);
    ulong q = ua / ub;
    bool neg = (a < 0) != (b < 0);
    ulong raw = neg ? (~q + 1UL) & ((T.sizeof == 8) ? 0xFFFF_FFFF_FFFF_FFFFUL : (1UL << (T.sizeof * 8)) - 1) : q & ((T.sizeof == 8) ? 0xFFFF_FFFF_FFFF_FFFFUL : (1UL << (T.sizeof * 8)) - 1);
    static if (T.sizeof == 8)
        return cast(T) raw;
    else static if (T.sizeof == 4)
        return cast(T)(raw & 0xFFFF_FFFFUL);
    else static if (T.sizeof == 2)
        return cast(T)(raw & 0xFFFFUL);
    else
        return cast(T)(raw & 0xFFUL);
}

/// B# `~`: C-style remainder, sign of the dividend, with wrap.
T bsMod(T)(T a, T b)
{
    if (b == 0)
        bsFail("modulo by zero");
    ulong ua = _uabs(a), ub = _uabs(b);
    ulong r = ua % ub;
    if (a < 0)
        r = (~r + 1UL);
    ulong mask = (T.sizeof == 8) ? 0xFFFF_FFFF_FFFF_FFFFUL : (1UL << (T.sizeof * 8)) - 1;
    r &= mask;
    static if (T.sizeof == 8)
        return cast(T) r;
    else static if (T.sizeof == 4)
        return cast(T)(r & 0xFFFF_FFFFUL);
    else static if (T.sizeof == 2)
        return cast(T)(r & 0xFFFFUL);
    else
        return cast(T)(r & 0xFFUL);
}

/// B# `^` on integers with non-negative exponent: exact modular power.
T bsPowI(T)(T base, T exp)
{
    if (exp < 0)
        bsFail("negative integer exponent needs a Double result");
    ulong mask = (T.sizeof == 8) ? 0xFFFF_FFFF_FFFF_FFFFUL : (1UL << (T.sizeof * 8)) - 1;
    ulong b = cast(ulong) base & mask;
    ulong e = cast(ulong) exp;
    ulong acc = 1;
    while (e > 0)
    {
        if (e & 1)
            acc = (acc * b) & mask;
        b = (b * b) & mask;
        e >>= 1;
    }
    static if (T.sizeof == 8)
        return cast(T) acc;
    else static if (T.sizeof == 4)
        return cast(T)(acc & 0xFFFF_FFFFUL);
    else static if (T.sizeof == 2)
        return cast(T)(acc & 0xFFFFUL);
    else
        return cast(T)(acc & 0xFFUL);
}

/// B# `^` with a float involved, or a negative integer exponent: Double.
double bsPowD(T, U)(T base, U exp)
{
    double raw;
    try
        raw = pow(cast(double) base, cast(double) exp);
    catch (Exception)
        bsFail("math domain error in power");
    if (isNaN(raw))
        bsFail("math domain error in power (complex result)");
    if (isInfinity(raw))
        bsFail("math overflow in power");
    return raw;
}

// ---- Casts (B# convert_numeric: trunc, NaN->0, inf->clamp, wrap) ----

long bsCastLong(T)(T v)
{
    static if (is(T == bool))
        static assert(false, "cast from Bool");
    else static if (is(T == string) || is(T == dchar))
        static assert(false, "cast from String/Char is Phase 5");
    else static if (is(T == float) || is(T == double))
    {
        double d = cast(double) v;
        if (isNaN(d))
            return 0;
        if (isInfinity(d))
            return d > 0 ? long.max : long.min;
        double t = trunc(d);
        enum double two63 = 9223372036854775808.0;
        enum double two64 = 18446744073709551616.0;
        if (t >= -two63 && t < two63)
            return cast(long) t;
        double r = fmod(t, two64);
        if (r >= two63)
            r -= two64;
        else if (r < -two63)
            r += two64;
        return cast(long) r;
    }
    else
        return cast(long) v;
}

int bsCastInteger(T)(T v)
{
    long w = bsCastLong(v);
    return cast(int)(w & 0xFFFF_FFFFUL);
}

short bsCastSingle(T)(T v)
{
    long w = bsCastLong(v);
    return cast(short)(w & 0xFFFFUL);
}

byte bsCastShort(T)(T v)
{
    long w = bsCastLong(v);
    return cast(byte)(w & 0xFFUL);
}

double bsCastDouble(T)(T v)
{
    static if (is(T == bool))
        static assert(false, "cast from Bool");
    else static if (is(T == string) || is(T == dchar))
        static assert(false, "cast from String/Char is Phase 5");
    else static if (is(T == float) || is(T == double))
        return cast(double) v;
    else
        return cast(double) v;
}

float bsCastFloat(T)(T v)
{
    return cast(float) bsCastDouble(v);
}

// ---- Strings ----

/// B# `"ab" * 3`: repetition, RUN107 on negative.
string bsRepeat(string s, long n)
{
    if (n < 0)
        bsFail("negative string repetition");
    import std.array : replicate;

    return s.replicate(cast(size_t) n);
}

// ---- Rendering (__writeln top-level semantics: strings raw) ----

string bsToStr(long v)
{
    return to!string(v);
}

string bsToStr(int v)
{
    return to!string(v);
}

string bsToStr(short v)
{
    return to!string(v);
}

string bsToStr(byte v)
{
    return to!string(v);
}

string bsToStr(double v)
{
    return bsDblStr(v);
}

string bsToStr(float v)
{
    return bsFltStr(v);
}

string bsToStr(bool v)
{
    return v ? "true" : "false";
}

string bsToStr(string v)
{
    return v;
}

string bsToStr(dchar v)
{
    return to!string(v);
}

// ---- __format arg semantics: historical repr (strings stay quoted) ----

string bsRepr(long v)
{
    return to!string(v);
}

string bsRepr(int v)
{
    return to!string(v);
}

string bsRepr(short v)
{
    return to!string(v);
}

string bsRepr(byte v)
{
    return to!string(v);
}

string bsRepr(double v)
{
    return bsDblStr(v);
}

string bsRepr(float v)
{
    return bsFltStr(v);
}

string bsRepr(bool v)
{
    return v ? "true" : "false";
}

string bsRepr(string v)
{
    return "\"" ~ v ~ "\"";
}

string bsRepr(dchar v)
{
    return to!string(v);
}

/// B# `__format(tmpl, args...)`: `{N}` substitution, unknown index kept.
string bsFormat(string tmpl, string[] args)
{
    import std.array : appender;

    auto out_ = appender!string();
    size_t i = 0;
    while (i < tmpl.length)
    {
        if (tmpl[i] == '{')
        {
            size_t j = i + 1;
            while (j < tmpl.length && tmpl[j] >= '0' && tmpl[j] <= '9')
                j++;
            if (j > i + 1 && j < tmpl.length && tmpl[j] == '}')
            {
                size_t idx = to!size_t(tmpl[i + 1 .. j]);
                if (idx < args.length)
                    out_.put(args[idx]);
                else
                    out_.put(tmpl[i .. j + 1]);
                i = j + 1;
                continue;
            }
        }
        out_.put(tmpl[i]);
        i++;
    }
    return out_.data;
}
