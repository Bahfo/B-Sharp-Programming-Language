// (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
// The B-Sharp Programming Language Written by B# Authors.
// Use of this source code is governed by GPLv3 License. 

import std.file : dirEntries, SpanMode, exists, mkdirRecurse, write;
import std.stdio : writeln, writefln;
import std.array : array; 
import std.format : format;
import std.path : buildPath, dirName;

struct Color {
    enum reset  = "\033[0m";
    enum bold   = "\033[1m";
    enum red    = "\033[31m";
    enum green  = "\033[32m";
    enum yellow = "\033[33m";
    enum cyan   = "\033[36m";
    enum gray   = "\033[90m";
}

enum CheckStatus {
    ok,
    missing,
    multiple
}

struct Requirement {
    string filename;
    string description;
    string templateContent;
}

struct CheckResult {
    Requirement req;
    CheckStatus status;
    size_t matchCount;
}

Requirement[] getBSharpRequirements() {
    return [
        Requirement(
            "bsharp.main",
            "Main entry point source file",
            q"BSHARP
// B# Main Entry Point
func main() {
    print("Hello, B# World!");
}
BSHARP"
        ),
        Requirement(
            "__init__.bsharp",
            "Project initialization script",
            q"BSHARP
// B# Package Initializer
#init {
    name: "MyBSharpProject",
    version: "0.1.0"
}
BSHARP"
        ),
        Requirement(
            "BSharpConfig.json",
            "Project build configuration file",
            q"JSON
{
    "name": "MyBSharpProject",
    "version": "1.0.0",
    "builder": true,
    "entry": "bsharp.main"
}
JSON"
        )
    ];
}

/* Scans for a single requirement */
CheckResult checkRequirement(string directory, Requirement req) {
    auto matches = dirEntries(directory, req.filename, SpanMode.depth).array;

    CheckStatus status;
    if (matches.length == 1) {
        status = CheckStatus.ok;
    } else if (matches.length > 1) {
        status = CheckStatus.multiple;
    } else {
        status = CheckStatus.missing;
    }

    return CheckResult(req, status, matches.length);
}

/* 
 * Scans the directory for all B# requirements and prints a formatted report.
 * Returns an array of CheckResult for downstream commands like populate().
 */
CheckResult[] doctor(string directory = ".") {
    writeln(
        Color.bold ~ Color.cyan ~ 
        "\n[•] Running B# Doctor in: " ~ directory ~ 
        Color.reset ~ "\n"
    );

    Requirement[] requirements = getBSharpRequirements();
    CheckResult[] results;
    size_t issuesFound = 0;

    foreach (req; requirements) {
        CheckResult res = checkRequirement(directory, req);
        results ~= res;

        final switch (res.status) {
            case CheckStatus.ok:
                writefln(
                    "  %s[✓]%s %s%s%s (%s)", 
                    Color.green, Color.reset, 
                    Color.bold, res.req.filename, Color.reset, 
                    res.req.description
                );
                break;

            case CheckStatus.missing:
                issuesFound++;
                writefln(
                    "  %s[✗]%s %s%s%s - %sMISSING%s", 
                    Color.red, Color.reset, 
                    Color.bold, res.req.filename, Color.reset, 
                    Color.red, Color.reset
                );
                writefln("      %s→ %s%s", Color.gray, res.req.description, Color.reset);
                break;

            case CheckStatus.multiple:
                issuesFound++;
                writefln(
                    "  %s[!]%s %s%s%s - %sMULTIPLE FOUND (%d files)%s", 
                    Color.yellow, Color.reset, 
                    Color.bold, res.req.filename, Color.reset, 
                    Color.yellow, res.matchCount, Color.reset
                );
                writefln(
                    "      %s→ Keep only one instance of this configuration file.%s", 
                    Color.gray, Color.reset
                );
                break;
        }
    }

    // Summary line
    writeln();
    if (issuesFound == 0) {
        writeln(
            Color.green ~ Color.bold ~ 
            "•• No issues found! Project is ready to build." ~ 
            Color.reset ~ "\n"
        );
    } else {
        writefln(
            "%s%s! Doctor found %d issue(s). Run 'bsharp populate' to generate missing files.%s\n", 
            Color.yellow, Color.bold, issuesFound, Color.reset
        );
    }

    return results;
}

/* 
 * Iterates through doctor results and generates default files for missing requirements.
 */
void populate(string directory, CheckResult[] results) {
    writeln(Color.bold ~ Color.cyan ~ "[•] Populating missing project files..." ~ Color.reset ~ "\n");

    size_t createdCount = 0;

    foreach (res; results) {
        if (res.status == CheckStatus.missing) {
            string targetPath = buildPath(directory, res.req.filename);
            string targetDir = dirName(targetPath);

            try {
                if (!exists(targetDir)) {
                    mkdirRecurse(targetDir);
                }

                write(targetPath, res.req.templateContent);
                writefln("  %s[+]%s", Color.green, Color.reset);
                writefln("    Created: %s%s%s", Color.bold, targetPath, Color.reset);
                createdCount++;
            } catch (Exception e) {
                writefln(
                    "  %s[✗] Failed to create %s: %s%s", 
                    Color.red, res.req.filename, e.msg, Color.reset
                );
            }
        }
    }

    if (createdCount == 0) {
        writeln(
            Color.gray ~ 
            "Nothing to populate. All required files are already present." ~ 
            Color.reset ~ "\n"
        );
    } else {
        writefln(
            "\n%s%sSuccessfully populated %d file(s).%s\n", 
            Color.green, Color.bold, createdCount, Color.reset
        );
    }
}

void main() {
    CheckResult[] results = doctor(".");
    populate(".", results);
}