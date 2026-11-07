"""Generate a conservative, version-neutral Unreal Engine C++ starter in a project workspace."""

from __future__ import annotations

import json
import os
import re
import secrets
import unicodedata
from pathlib import Path

from hydrahive.projects._paths import ensure_workspace

from .models import WorkspaceProject

_ENGINE_DIR = "unreal"
_NAME_PARTS = re.compile(r"[^A-Za-z0-9]+")


class UnrealProjectError(RuntimeError):
    pass


def project_name(title: str, project_id: str) -> str:
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    parts = [part for part in _NAME_PARTS.split(ascii_title) if part]
    name = "".join(part[:1].upper() + part[1:] for part in parts)
    if not name or not name[0].isalpha():
        name = f"Game{project_id.replace('-', '')[:8]}"
    return name[:48]


def project_file(name: str) -> str:
    return f"{_ENGINE_DIR}/{name}/{name}.uproject"


def _directory(root: Path, relative: Path) -> Path:
    current = root
    for part in relative.parts:
        if part in ("", ".", ".."):
            raise UnrealProjectError("game_studio_unreal_path_invalid")
        current = current / part
        if current.is_symlink():
            raise UnrealProjectError("game_studio_unreal_symlink")
        current.mkdir(mode=0o2775, exist_ok=True)
    if not current.resolve().is_relative_to(root.resolve()):
        raise UnrealProjectError("game_studio_unreal_path_escape")
    return current


def _atomic_write(path: Path, content: str) -> None:
    if path.is_symlink():
        raise UnrealProjectError("game_studio_unreal_symlink")
    if path.exists():
        try:
            if path.read_text(encoding="utf-8") == content:
                return
        except OSError as exc:
            raise UnrealProjectError("game_studio_unreal_file_unreadable") from exc
        raise UnrealProjectError("game_studio_unreal_file_exists")
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o664)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o664)
    finally:
        temporary.unlink(missing_ok=True)


def _files(project: WorkspaceProject, name: str) -> dict[str, str]:
    uproject = {
        "FileVersion": 3,
        "Category": "Games",
        "Description": project.idea,
        "Modules": [{"Name": name, "Type": "Runtime", "LoadingPhase": "Default"}],
    }
    build_cs = f'''using UnrealBuildTool;

public class {name} : ModuleRules
{{
    public {name}(ReadOnlyTargetRules Target) : base(Target)
    {{
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new string[] {{ "Core", "CoreUObject", "Engine", "InputCore" }});
    }}
}}
'''
    game_target = f'''using UnrealBuildTool;
using System.Collections.Generic;

public class {name}Target : TargetRules
{{
    public {name}Target(TargetInfo Target) : base(Target)
    {{
        Type = TargetType.Game;
        ExtraModuleNames.Add("{name}");
    }}
}}
'''
    editor_target = f'''using UnrealBuildTool;
using System.Collections.Generic;

public class {name}EditorTarget : TargetRules
{{
    public {name}EditorTarget(TargetInfo Target) : base(Target)
    {{
        Type = TargetType.Editor;
        ExtraModuleNames.Add("{name}");
    }}
}}
'''
    module_h = '''#pragma once

#include "CoreMinimal.h"
'''
    module_cpp = f'''#include "{name}.h"
#include "Modules/ModuleManager.h"

IMPLEMENT_PRIMARY_GAME_MODULE(FDefaultGameModuleImpl, {name}, "{name}");
'''
    character_h = f'''#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "{name}Character.generated.h"

class UCameraComponent;
class USpringArmComponent;

UCLASS()
class {name.upper()}_API A{name}Character : public ACharacter
{{
    GENERATED_BODY()

public:
    A{name}Character();

protected:
    virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

private:
    void MoveForward(float Value);
    void MoveRight(float Value);

    UPROPERTY(VisibleAnywhere, Category = "Camera")
    USpringArmComponent* CameraBoom;

    UPROPERTY(VisibleAnywhere, Category = "Camera")
    UCameraComponent* FollowCamera;
}};
'''
    character_cpp = f'''#include "{name}Character.h"

#include "Camera/CameraComponent.h"
#include "Components/InputComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "GameFramework/SpringArmComponent.h"

A{name}Character::A{name}Character()
{{
    CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
    CameraBoom->SetupAttachment(RootComponent);
    CameraBoom->TargetArmLength = 500.0f;
    CameraBoom->bUsePawnControlRotation = true;

    FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
    FollowCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
    FollowCamera->bUsePawnControlRotation = false;

    bUseControllerRotationYaw = false;
    GetCharacterMovement()->bOrientRotationToMovement = true;
}}

void A{name}Character::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{{
    Super::SetupPlayerInputComponent(PlayerInputComponent);
    PlayerInputComponent->BindAxis(TEXT("MoveForward"), this, &A{name}Character::MoveForward);
    PlayerInputComponent->BindAxis(TEXT("MoveRight"), this, &A{name}Character::MoveRight);
    PlayerInputComponent->BindAxis(TEXT("Turn"), this, &APawn::AddControllerYawInput);
    PlayerInputComponent->BindAxis(TEXT("LookUp"), this, &APawn::AddControllerPitchInput);
    PlayerInputComponent->BindAction(TEXT("Jump"), IE_Pressed, this, &ACharacter::Jump);
    PlayerInputComponent->BindAction(TEXT("Jump"), IE_Released, this, &ACharacter::StopJumping);
}}

void A{name}Character::MoveForward(float Value)
{{
    if (Controller && Value != 0.0f)
    {{
        const FRotator Rotation(0.0f, Controller->GetControlRotation().Yaw, 0.0f);
        AddMovementInput(FRotationMatrix(Rotation).GetUnitAxis(EAxis::X), Value);
    }}
}}

void A{name}Character::MoveRight(float Value)
{{
    if (Controller && Value != 0.0f)
    {{
        const FRotator Rotation(0.0f, Controller->GetControlRotation().Yaw, 0.0f);
        AddMovementInput(FRotationMatrix(Rotation).GetUnitAxis(EAxis::Y), Value);
    }}
}}
'''
    goal_h = f'''#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "{name}Goal.generated.h"

class UBoxComponent;
class UPrimitiveComponent;
class UStaticMeshComponent;

UCLASS()
class {name.upper()}_API A{name}Goal : public AActor
{{
    GENERATED_BODY()

public:
    A{name}Goal();

private:
    UFUNCTION()
    void OnGoalReached(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
        UPrimitiveComponent* OtherComponent, int32 OtherBodyIndex, bool bFromSweep,
        const FHitResult& SweepResult);

    UPROPERTY(VisibleAnywhere)
    UStaticMeshComponent* GoalMesh;

    UPROPERTY(VisibleAnywhere)
    UBoxComponent* GoalTrigger;
}};
'''
    goal_cpp = f'''#include "{name}Goal.h"

#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Character.h"
#include "UObject/ConstructorHelpers.h"

A{name}Goal::A{name}Goal()
{{
    PrimaryActorTick.bCanEverTick = false;

    GoalMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("GoalMesh"));
    SetRootComponent(GoalMesh);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded())
    {{
        GoalMesh->SetStaticMesh(Cube.Object);
        GoalMesh->SetRelativeScale3D(FVector(1.0f, 1.0f, 2.0f));
    }}

    GoalTrigger = CreateDefaultSubobject<UBoxComponent>(TEXT("GoalTrigger"));
    GoalTrigger->SetupAttachment(RootComponent);
    GoalTrigger->SetBoxExtent(FVector(120.0f));
    GoalTrigger->SetCollisionProfileName(TEXT("Trigger"));
    GoalTrigger->OnComponentBeginOverlap.AddDynamic(this, &A{name}Goal::OnGoalReached);
}}

void A{name}Goal::OnGoalReached(UPrimitiveComponent*, AActor* OtherActor, UPrimitiveComponent*, int32, bool, const FHitResult&)
{{
    if (Cast<ACharacter>(OtherActor))
    {{
        const FString Message = TEXT("Ziel erreicht");
        UE_LOG(LogTemp, Display, TEXT("%s"), *Message);
        if (GEngine)
        {{
            GEngine->AddOnScreenDebugMessage(-1, 8.0f, FColor::Green, Message);
        }}
    }}
}}
'''
    game_mode_h = f'''#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "{name}GameMode.generated.h"

UCLASS()
class {name.upper()}_API A{name}GameMode : public AGameModeBase
{{
    GENERATED_BODY()

public:
    A{name}GameMode();
    virtual void StartPlay() override;
    virtual AActor* ChoosePlayerStart_Implementation(AController* Player) override;
}};
'''
    game_mode_cpp = f'''#include "{name}GameMode.h"

#include "{name}Character.h"
#include "{name}Goal.h"
#include "Components/DirectionalLightComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/PlayerStart.h"
#include "UObject/UObjectGlobals.h"

A{name}GameMode::A{name}GameMode()
{{
    DefaultPawnClass = A{name}Character::StaticClass();
}}

AActor* A{name}GameMode::ChoosePlayerStart_Implementation(AController* Player)
{{
    if (UWorld* World = GetWorld())
    {{
        return World->SpawnActor<APlayerStart>(APlayerStart::StaticClass(), FVector(0.0f, 0.0f, 120.0f), FRotator::ZeroRotator);
    }}
    return Super::ChoosePlayerStart_Implementation(Player);
}}

void A{name}GameMode::StartPlay()
{{
    if (UWorld* World = GetWorld())
    {{
        if (UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube")))
        {{
            AStaticMeshActor* Floor = World->SpawnActor<AStaticMeshActor>(FVector(0.0f, 0.0f, -50.0f), FRotator::ZeroRotator);
            Floor->GetStaticMeshComponent()->SetStaticMesh(Cube);
            Floor->SetActorScale3D(FVector(20.0f, 20.0f, 0.5f));
        }}
        World->SpawnActor<A{name}Goal>(FVector(1000.0f, 0.0f, 100.0f), FRotator::ZeroRotator);
        ADirectionalLight* Light = World->SpawnActor<ADirectionalLight>(FVector::ZeroVector, FRotator(-45.0f, -30.0f, 0.0f));
        if (Light && Light->GetLightComponent())
        {{
            Light->GetLightComponent()->SetIntensity(5.0f);
        }}
    }}
    Super::StartPlay();
}}
'''
    engine_ini = f'''[/Script/EngineSettings.GameMapsSettings]
GameDefaultMap=/Engine/Maps/Entry
EditorStartupMap=/Engine/Maps/Entry
GlobalDefaultGameMode=/Script/{name}.{name}GameMode

[/Script/Engine.Engine]
+ActiveGameNameRedirects=(OldGameName="/Script/TP_ThirdPerson",NewGameName="/Script/{name}")
'''
    input_ini = '''[/Script/Engine.InputSettings]
+AxisMappings=(AxisName="MoveForward",Scale=1.000000,Key=W)
+AxisMappings=(AxisName="MoveForward",Scale=-1.000000,Key=S)
+AxisMappings=(AxisName="MoveRight",Scale=1.000000,Key=D)
+AxisMappings=(AxisName="MoveRight",Scale=-1.000000,Key=A)
+AxisMappings=(AxisName="Turn",Scale=1.000000,Key=MouseX)
+AxisMappings=(AxisName="LookUp",Scale=-1.000000,Key=MouseY)
+ActionMappings=(ActionName="Jump",Key=SpaceBar)
bAlwaysShowTouchInterface=False
'''
    readme = f'''# {project.title} — Unreal Engine

Dieses C++-Starterprojekt wurde von HydraHive Game Studio erzeugt und liegt vollständig im Projekt-Workspace.

- Unreal-Version: `{project.engine_version}` (`auto` bedeutet: beim lokalen Öffnen auswählen)
- Idee: {project.idea or "Noch nicht beschrieben."}
- Genre: {project.genre or "Noch nicht festgelegt."}
- Spieleraktion: {project.core_action or "Noch nicht festgelegt."}
- Sichtbares Ergebnis: {project.success_condition or "Noch nicht festgelegt."}

## Öffnen unter Linux

Öffne `{name}.uproject` in Unreal. Beim ersten Öffnen fragt Unreal, ob die Module gebaut werden sollen – mit Ja bestätigen. Danach ganz normal in Unreal arbeiten.

Der Starter enthält eine steuerbare Spielfigur, eine Lauf-/Sprungsteuerung, eine erzeugte Bodenfläche und ein erreichbares Ziel. Das ist echter editierbarer C++-Quellcode; es werden keine fertigen Builds oder Testergebnisse behauptet.
'''
    gitignore = '''Binaries/
DerivedDataCache/
Intermediate/
Saved/
.vscode/
.idea/
*.sln
*.suo
*.opensdf
*.sdf
'''
    marker = json.dumps(
        {
            "generator": "hydrahive-game-studio",
            "schema_version": 1,
            "engine": "unreal",
            "engine_version": project.engine_version,
            "project_file": f"{name}.uproject",
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    return {
        f"{name}.uproject": json.dumps(uproject, ensure_ascii=False, indent=2) + "\n",
        ".gitignore": gitignore,
        "README.md": readme,
        "Config/DefaultEngine.ini": engine_ini,
        "Config/DefaultInput.ini": input_ini,
        "Content/.gitkeep": "",
        f"Source/{name}.Target.cs": game_target,
        f"Source/{name}Editor.Target.cs": editor_target,
        f"Source/{name}/{name}.Build.cs": build_cs,
        f"Source/{name}/{name}.h": module_h,
        f"Source/{name}/{name}.cpp": module_cpp,
        f"Source/{name}/{name}Character.h": character_h,
        f"Source/{name}/{name}Character.cpp": character_cpp,
        f"Source/{name}/{name}Goal.h": goal_h,
        f"Source/{name}/{name}Goal.cpp": goal_cpp,
        f"Source/{name}/{name}GameMode.h": game_mode_h,
        f"Source/{name}/{name}GameMode.cpp": game_mode_cpp,
        ".game-studio-generated.json": marker,
    }


def generate(project: WorkspaceProject) -> WorkspaceProject:
    if project.engine != "unreal":
        raise UnrealProjectError("game_studio_unreal_engine_required")
    if project.current_step < 4 or not (project.core_action.strip() and project.success_condition.strip()):
        raise UnrealProjectError("game_studio_step_incomplete")
    name = project.engine_project_name or project_name(project.title, project.project_id)
    root = ensure_workspace(project.project_id)
    target = _directory(root, Path(_ENGINE_DIR) / name)
    files = _files(project, name)
    marker = ".game-studio-generated.json"
    targets: dict[str, tuple[Path, str]] = {}
    for relative, content in files.items():
        path = target / relative
        if Path(relative).parent != Path("."):
            _directory(target, Path(relative).parent)
        if path.is_symlink():
            raise UnrealProjectError("game_studio_unreal_symlink")
        try:
            if path.exists():
                if project.engine_project_ready:
                    continue
                if path.read_text(encoding="utf-8") != content:
                    raise UnrealProjectError("game_studio_unreal_file_exists")
        except OSError as exc:
            raise UnrealProjectError("game_studio_unreal_file_unreadable") from exc
        targets[relative] = (path, content)

    for relative, (path, content) in targets.items():
        if relative != marker:
            _atomic_write(path, content)
    if marker in targets:
        _atomic_write(*targets[marker])

    return project.model_copy(update={
        "engine_project_name": name,
        "engine_project_path": project_file(name),
        "engine_project_ready": True,
    })
