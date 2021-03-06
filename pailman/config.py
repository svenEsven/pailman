import json
from pathlib import Path

import yaml
from jsonschema import validate
from yaml.resolver import Resolver

from pailman.defaults import (  # noqa: F401
    BLUEPRINT_KEYS,
    BLUEPRINT_SCHEMA,
    BLUEPRINTS_GLOB,
    CONFIG_SCHEMA,
    CONFIG_VERSION,
    DEFAULT_BLUEPRINTS_DIR,
    JAIL_KEYS,
)


# https://stackoverflow.com/questions/36463531/pyyaml-automatically-converting-certain-keys-to-boolean-values
def _configure_yaml_parser():
    # remove resolver entries for On/Off/Yes/No
    for ch in "OoYyNn":
        if len(Resolver.yaml_implicit_resolvers[ch]) == 1:
            del Resolver.yaml_implicit_resolvers[ch]
        else:
            Resolver.yaml_implicit_resolvers[ch] = [
                x
                for x in Resolver.yaml_implicit_resolvers[ch]
                if x[0] != "tag:yaml.org,2002:bool"
            ]


_configure_yaml_parser()


def parse_config(cfg):
    contents = yaml.safe_load(cfg)
    return contents


def read_config(filename):
    with open(filename) as file:
        contents = yaml.safe_load(file)
        return contents


def find_blueprint_config_files(dir=DEFAULT_BLUEPRINTS_DIR, glob=BLUEPRINTS_GLOB):
    return Path(dir).glob(glob)


def read_blueprints(dir=DEFAULT_BLUEPRINTS_DIR, glob=BLUEPRINTS_GLOB):
    configs = {p: read_config(p) for p in find_blueprint_config_files(dir, glob)}
    return configs


def read_schema(filename):
    with open(filename) as file:
        contents = json.load(file)
        return contents


def validate_config(cfg, schema=read_schema(CONFIG_SCHEMA)):
    return validate(schema=schema, instance=json.loads(json.dumps(cfg)))


def validate_blueprint(blueprint):
    return validate(
        schema=read_schema(BLUEPRINT_SCHEMA), instance=json.loads(json.dumps(blueprint))
    )


def collection_from_string(x, sep=" "):
    return x.split(sep)


# replaces space separated strings with lists
def normalize_blueprint(blueprint):
    root = blueprint[BLUEPRINT_KEYS.BLUEPRINT]
    name_key = next(iter(root.items()))[0]
    attrs = root[name_key]

    for key in [BLUEPRINT_KEYS.VARS, BLUEPRINT_KEYS.REQVARS, BLUEPRINT_KEYS.PKGS]:
        if key in attrs and attrs[key] is not None and isinstance(attrs[key], str):
            attrs[key] = collection_from_string(attrs[key])

    return blueprint


# blueprint must be validated
def validate_jail_config(jail, jailcfg, blueprint):
    blueprintref = jailcfg[JAIL_KEYS.BLUEPRINT]
    bp = normalize_blueprint(blueprint)

    # this blueprint is validated, we can assume 'blueprint' to exist
    if blueprintref not in bp[BLUEPRINT_KEYS.BLUEPRINT]:
        print(
            "error: jail {} references undefined blueprint {}".format(
                jail, blueprintref
            )
        )
        return False, {}
    else:
        blueprint_config = {}
        blueprint_instance = bp[BLUEPRINT_KEYS.BLUEPRINT][blueprintref]
        bvars = blueprint_instance.get(BLUEPRINT_KEYS.VARS, [])
        required_vars = blueprint_instance.get(BLUEPRINT_KEYS.REQVARS, [])

        for var in required_vars:
            if var not in jailcfg:
                print(
                    "variable '{}' required by blueprint '{}' but not configured for jail '{}'".format(
                        var, blueprintref, jail
                    )
                )
                return False, {}
            blueprint_config[var] = jailcfg[var]

        for var in bvars:
            if var in jailcfg:
                blueprint_config[var] = jailcfg[var]

        seen = (
            set(required_vars)
            .union(bvars)
            .union([JAIL_KEYS.BLUEPRINT, JAIL_KEYS.IP4_ADDR, JAIL_KEYS.GATEWAY])
        )

        unseen = set(jailcfg).difference(seen)
        if len(unseen) > 0:
            print(
                "variable{} {} found in configuration for jail '{}' but not used by blueprint '{}'".format(
                    "s" if len(unseen) > 1 else "",
                    ", ".join("'" + x + "'" for x in unseen),
                    jail,
                    blueprintref,
                )
            )

        return True, blueprint_config
