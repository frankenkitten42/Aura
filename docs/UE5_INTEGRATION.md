# UE5 Integration Guide

This guide explains how to connect the Living Soundscape Engine (AURA) to Unreal Engine 5.

## Integration Options

| Method | Complexity | Latency | Best For |
|--------|------------|---------|----------|
| HTTP Server | Low | ~10-50ms | Prototyping, testing |
| WebSocket | Medium | ~1-5ms | Real-time, production |
| JSON File | Very Low | ~100ms | Offline, batch processing |
| C++ Port | High | <1ms | Shipping game |

## Option 1: HTTP Server (Recommended for Development)

### Step 1: Start the Python Server

```bash
# In Termux or terminal
cd lse
python ue5_server.py --port 8080 --auto-tick
```

### Step 2: UE5 Blueprint Setup (VaRest Plugin)

1. Install VaRest plugin from Marketplace
2. Create a new Actor Blueprint: `BP_AURAManager`

```
Event BeginPlay
    → Set Timer by Function Name
        Function: "FetchParameters"
        Time: 0.1 (10 Hz)
        Looping: true

Function: FetchParameters
    → VaRest: Call URL
        URL: "http://localhost:8080/parameters"
        Verb: GET
    → On Response:
        → Parse JSON
        → Apply Parameters (see below)
```

### Step 3: Apply Parameters in UE5

```cpp
// In C++ or Blueprint
void AMyGameMode::ApplyAURAParameters(const FJsonObject& Data)
{
    // Get region data
    auto Regions = Data.GetObjectField("regions");
    auto TownData = Regions->GetObjectField("town_square");
    
    // Pressure
    float SDI = TownData->GetObjectField("pressure")->GetNumberField("Pressure_SDI");
    float VDI = TownData->GetObjectField("pressure")->GetNumberField("Pressure_VDI");
    
    // Apply to post-process
    PostProcessVolume->Settings.ColorSaturation = FMath::Lerp(1.0f, 0.85f, VDI);
    PostProcessVolume->Settings.BloomIntensity = FMath::Lerp(0.0f, 0.3f, VDI);
    
    // Wildlife spawn rate
    auto Wildlife = TownData->GetObjectField("wildlife");
    float SpawnRate = Wildlife->GetNumberField("Wildlife_SpawnRate");
    WildlifeSpawner->SetSpawnRateMultiplier(SpawnRate);
    
    // Motion coherence
    auto Motion = TownData->GetObjectField("motion");
    float WindDir = Motion->GetNumberField("Wind_Direction");
    float Coherence = Motion->GetNumberField("Foliage_WaveCoherence");
    
    FoliageSystem->SetWindDirection(WindDir);
    FoliageSystem->SetCoherence(Coherence);
}
```

### Step 4: Send Population Updates to Server

```cpp
void AMyGameMode::UpdateRegionPopulation(FString RegionId, float Population)
{
    // Create JSON body
    TSharedPtr<FJsonObject> Body = MakeShareable(new FJsonObject);
    Body->SetNumberField("population", Population);
    
    // POST to server
    FString URL = FString::Printf(TEXT("http://localhost:8080/region/%s/pop"), *RegionId);
    
    TSharedRef<IHttpRequest> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(URL);
    Request->SetVerb("POST");
    Request->SetHeader("Content-Type", "application/json");
    Request->SetContentAsString(JsonToString(Body));
    Request->ProcessRequest();
}
```

## Option 2: JSON File Exchange

For simpler setups or offline processing.

### Python Side (Export)

```python
from vde import PressureCoordinator
import json

coordinator = PressureCoordinator()
coordinator.add_region("town", (0, 0))
coordinator.set_population("town", 0.65)

for _ in range(100):
    coordinator.update(0.1)

# Export to file
with open("lse_params.json", "w") as f:
    json.dump(coordinator.to_ue5_json(), f, indent=2)
```

### UE5 Side (Import)

```cpp
// In UE5 C++
void UAURAManager::LoadParametersFromFile()
{
    FString JsonString;
    FFileHelper::LoadFileToString(JsonString, TEXT("lse_params.json"));
    
    TSharedPtr<FJsonObject> JsonObject;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonString);
    
    if (FJsonSerializer::Deserialize(Reader, JsonObject))
    {
        ApplyParameters(JsonObject);
    }
}
```

## Option 3: WebSocket (Real-Time)

For lowest latency real-time updates.

### Python Server with WebSocket

```python
# pip install websockets
import asyncio
import websockets
import json
from vde import PressureCoordinator

coordinator = PressureCoordinator()
# ... setup regions ...

async def handler(websocket, path):
    async for message in websocket:
        data = json.loads(message)
        
        if data["type"] == "set_population":
            coordinator.set_population(data["region"], data["value"])
        
        elif data["type"] == "get_parameters":
            coordinator.update(0.016)
            await websocket.send(json.dumps(coordinator.to_ue5_json()))

asyncio.run(websockets.serve(handler, "localhost", 8765))
```

### UE5 WebSocket Client

Use the WebSocket plugin or integrate a C++ WebSocket library.

## Material Parameter Collection Setup

Create an MPC in UE5 to receive AURA parameters:

### 1. Create MPC Asset

```
Content Browser → Right Click → Materials → Material Parameter Collection
Name: MPC_AURA
```

### 2. Add Parameters

| Name | Type | Default |
|------|------|---------|
| AURA_Saturation | Scalar | 1.0 |
| AURA_Contrast | Scalar | 1.0 |
| AURA_GrassHeight | Scalar | 1.0 |
| AURA_GrassColor | Scalar | 0.0 |
| AURA_WearAmount | Scalar | 0.0 |
| AURA_WindDirection | Scalar | 0.0 |
| AURA_WindStrength | Scalar | 0.5 |
| AURA_Coherence | Scalar | 1.0 |

### 3. Update from Blueprint/C++

```cpp
UMaterialParameterCollectionInstance* MPCInstance = 
    GetWorld()->GetParameterCollectionInstance(MPC_AURA);

MPCInstance->SetScalarParameterValue("AURA_Saturation", 1.0f - VDI * 0.15f);
MPCInstance->SetScalarParameterValue("AURA_GrassHeight", 1.0f - WearAmount * 0.7f);
MPCInstance->SetScalarParameterValue("AURA_WindDirection", WindDirection);
```

### 4. Use in Materials

In your grass/foliage materials:
```
Material Editor:
    CollectionParameter (MPC_AURA, AURA_GrassHeight)
    → Multiply with World Position Offset Z
```

## Niagara Integration

### Wildlife Spawner

```cpp
// In Niagara Module Script
input float SpawnRateMultiplier;  // From AURA

// Modify spawn rate
SpawnRate = BaseSpawnRate * SpawnRateMultiplier;
```

### Particle Coherence

```cpp
// Wind direction from AURA
float3 WindDir = float3(cos(WindDirection), sin(WindDirection), 0);

// Apply coherence
float3 Velocity = lerp(RandomVelocity, WindDir * WindStrength, Coherence);
```

## Post-Process Integration

### Blueprint Setup

```
Get AURA Parameters
    → Branch (VDI > 0.3)
        True:
            → Set Post Process Settings
                Saturation: Lerp(1.0, 0.85, VDI)
                Bloom: Lerp(0.0, 0.3, VDI)
                Vignette: Lerp(0.0, 0.2, VDI)
```

### C++ Setup

```cpp
void APostProcessManager::UpdateFromAURA(float VDI)
{
    FPostProcessSettings& Settings = PostProcessVolume->Settings;
    
    // Subtle desaturation
    Settings.ColorSaturation.W = FMath::Lerp(1.0f, 0.85f, VDI);
    
    // Soft bloom
    Settings.BloomIntensity = FMath::Lerp(0.0f, 0.3f, VDI);
    
    // Vignette
    Settings.VignetteIntensity = FMath::Lerp(0.0f, 0.2f, VDI);
    
    // Chromatic aberration (subtle)
    Settings.SceneFringeIntensity = FMath::Lerp(0.0f, 0.15f, VDI);
}
```

## Complete UE5 Actor Example

```cpp
// AURAManager.h
UCLASS()
class AAURAManager : public AActor
{
    GENERATED_BODY()

public:
    UPROPERTY(EditAnywhere)
    FString ServerURL = "http://localhost:8080";
    
    UPROPERTY(EditAnywhere)
    float UpdateRate = 0.1f;
    
    UPROPERTY(EditAnywhere)
    UMaterialParameterCollection* MPC;
    
    UPROPERTY(EditAnywhere)
    APostProcessVolume* PostProcess;

private:
    FTimerHandle UpdateTimer;
    
    void FetchParameters();
    void ApplyParameters(TSharedPtr<FJsonObject> Data);
    void UpdatePopulation(FString Region, float Pop);
};

// AURAManager.cpp
void AAURAManager::BeginPlay()
{
    Super::BeginPlay();
    
    GetWorldTimerManager().SetTimer(
        UpdateTimer, this, &AAURAManager::FetchParameters, 
        UpdateRate, true
    );
}

void AAURAManager::FetchParameters()
{
    TSharedRef<IHttpRequest> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(ServerURL + "/parameters");
    Request->SetVerb("GET");
    
    Request->OnProcessRequestComplete().BindLambda(
        [this](FHttpRequestPtr Req, FHttpResponsePtr Resp, bool Success)
        {
            if (Success && Resp.IsValid())
            {
                TSharedPtr<FJsonObject> Json;
                TSharedRef<TJsonReader<>> Reader = 
                    TJsonReaderFactory<>::Create(Resp->GetContentAsString());
                
                if (FJsonSerializer::Deserialize(Reader, Json))
                {
                    ApplyParameters(Json);
                }
            }
        }
    );
    
    Request->ProcessRequest();
}

void AAURAManager::ApplyParameters(TSharedPtr<FJsonObject> Data)
{
    // Get first region (or iterate all)
    auto Regions = Data->GetObjectField("regions");
    
    for (auto& Pair : Regions->Values)
    {
        auto RegionData = Pair.Value->AsObject();
        auto Pressure = RegionData->GetObjectField("pressure");
        
        float SDI = Pressure->GetNumberField("Pressure_SDI");
        float VDI = Pressure->GetNumberField("Pressure_VDI");
        
        // Update MPC
        if (MPC)
        {
            auto MPCInst = GetWorld()->GetParameterCollectionInstance(MPC);
            MPCInst->SetScalarParameterValue("AURA_VDI", VDI);
            MPCInst->SetScalarParameterValue("AURA_SDI", SDI);
        }
        
        // Update Post-Process
        if (PostProcess)
        {
            PostProcess->Settings.ColorSaturation.W = 1.0f - VDI * 0.15f;
            PostProcess->Settings.BloomIntensity = VDI * 0.3f;
        }
        
        // Update Motion
        if (RegionData->HasField("motion"))
        {
            auto Motion = RegionData->GetObjectField("motion");
            float WindDir = Motion->GetNumberField("Wind_Direction");
            float Coherence = Motion->GetNumberField("Foliage_WaveCoherence");
            
            // Apply to wind system
            // ...
        }
    }
}
```

## Testing in Termux

```bash
# 1. Start server in one Termux session
python ue5_server.py --port 8080 --auto-tick

# 2. In another session, test with curl
curl http://localhost:8080/status
curl http://localhost:8080/parameters
curl -X POST http://localhost:8080/region/town_square/pop -d '{"population": 0.85}'

# 3. Or run the interactive simulator
python termux_simulator.py --simple
```

## Troubleshooting

### Server not reachable from UE5
- Check firewall settings
- Use `--host 0.0.0.0` to bind to all interfaces
- If on Android, use your device's IP instead of localhost

### Parameters not updating
- Verify auto-tick is running: `GET /status`
- Check UE5 is parsing JSON correctly
- Add logging to see received values

### Performance issues
- Reduce update rate (10 Hz is usually enough)
- Only fetch parameters for nearby regions
- Cache parameters client-side

## Production Considerations

For shipping a game, consider:

1. **Port to C++**: Rewrite the AURA logic in C++ for zero latency
2. **Bake presets**: Pre-calculate common scenarios
3. **Simplify**: Use lookup tables instead of full simulation
4. **Profile**: Measure actual performance impact

The Python server is ideal for development and testing. For production, either port to C++ or use a more efficient communication method like shared memory.
