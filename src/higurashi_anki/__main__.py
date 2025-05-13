import click

import rich
from pathlib import Path
import json
import urllib.request


def request(action, **params):
    return {"action": action, "params": params, "version": 6}


def invoke(action, **params):
    requestJson = json.dumps(request(action, **params)).encode("utf-8")
    response = json.load(
        urllib.request.urlopen(
            urllib.request.Request("http://127.0.0.1:8765", requestJson)
        )
    )
    if len(response) != 2:
        raise Exception("response has an unexpected number of fields")
    if "error" not in response:
        raise Exception("response is missing required error field")
    if "result" not in response:
        raise Exception("response is missing required result field")
    if response["error"] is not None:
        if response["error"] == "cannot create note because it is a duplicate":
            return
        raise Exception(response["error"])
    return response["result"]


def anki(sentence, sentence_audio, main_definition, misc_info):
    if not sentence:
        print(sentence, sentence_audio, main_definition, misc_info)
        return
    note = {
        "deckName": "Test",
        "modelName": "Sentence",
        "fields": {
            "Sentence": sentence,
            "MainDefinition": main_definition,
            "MiscInfo": misc_info,
        },
        "options": {
            "allowDuplicate": False,
        },
    }

    if sentence_audio:
        note["fields"]["SentenceAudio"] = f"[sound:{sentence_audio}.ogg]"
        # note["audio"] = [{"url": str(sentence_audio), "filename": sentence_audio.name, "fields": ["SentenceAudio"]}]
    print(note)
    invoke("addNote", note=note)

import re
def split_args_robust(arg_string: str):
    args = []
    current = ''
    in_quotes = False
    escape = False

    for char in arg_string:
        if escape:
            current += char
            escape = False
        elif char == '\\':
            current += char  # Keep the backslash for correct escaping
            escape = True
        elif char == '"':
            current += char
            in_quotes = not in_quotes
        elif char == ',' and not in_quotes:
            args.append(current.strip())
            current = ''
        else:
            current += char

    if current:
        args.append(current.strip())
    
    return args

@click.command()
@click.argument("path", type=click.Path())
def run(path: str):
    """PATH to the "Higurashi When They Cry" directory.
    For example: "~/.local/share/Steam/steamapps/common/Higurashi When They Cry"."""
    path: Path = Path(path)
    data_path = path / "HigurashiEp01_Data/StreamingAssets"
    scripts_path = data_path / "Update"

    for script in scripts_path.glob("*.txt"):
        file = script.name
        text = script.read_text().replace(",\n", ",").replace("\u3000", "")
        text = text.split("\n")
        current_voice = None
        needed_commands = ["OutputLine(", "ClearMessage(", "ModPlayVoiceLS("]
        current_line = ""
        current_translation = ""
        index = 0
        for line in text:
            line = line.strip()
            needed = False
            current_command = None
            for command in needed_commands:
                if command in line:
                    needed = True
                    current_command = command[:-1]
            if not needed:
                continue
            start_args = line.find(current_command) + 1
            end_args = line.find(")", start_args)
            if current_command == "ModPlayVoiceLS" and current_voice:
                anki(
                    current_line,
                    current_voice,
                    current_translation,
                    f"{file} - {index}",
                )
                current_line = ""
                current_translation = ""
                current_voice = None
                index += 1
            if current_command == "ModPlayVoiceLS":
                args =split_args_robust(line[start_args + len(current_command) : end_args])
                print(line, "|", args)
                current_voice = f"{args[2].strip()[1:-1]}"
            elif current_command == "OutputLine":
                args =  split_args_robust(line[start_args + len(current_command) : end_args])
                print(line, "|", args)
                if args[0] == "NULL":
                    current_line += args[1][1:-1]
                    current_translation += args[3][1:-1].replace('\\"', '"')
                else:
                    current_line += (
                        args[0][1:-1]
                        .replace('\\"', '"')
                        .replace("<color=", '<span style="color:')
                        .replace(">", '">')
                        .replace('</color">', "</span>")
                    )
                    current_translation += (
                        args[2][1:-1]
                        .replace('\\"', '"')
                        .replace("<color=", '<span style="color:')
                        .replace(">", '">')
                        .replace('</color">', ":</span>")
                        + " "
                    )
            elif current_command == "ClearMessage":
                anki(
                    current_line,
                    current_voice,
                    current_translation,
                    f"{file} - {index}",
                )
                current_line = ""
                current_translation = ""
                current_voice = None
                index += 1
            else:
                print(line, current_command, start_args)


def main():
    run()


if __name__ == "__main__":
    main()
